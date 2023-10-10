import base64
import time
import multiprocessing
from signal import signal, SIGINT, SIGTERM
import rpyc
from ludo import Ludo, GameConfig, LudoModel
import json
import random
import numpy as np
from evaluator import EvaluatorMain
from concurrent.futures import ThreadPoolExecutor

TRAIN_SERVER_IP = "localhost"
TRAIN_SERVER_PORT = 18861
EVALUATOR_PORT = 18862
NUM_GAMES = 1
EVALUATION_BATCH_SIZE = 512
MAX_SIMULATIONS = 100

class MCTSNode:
    def __init__(self, state, available_moves):
        self.state = state
        self.available_moves = available_moves
        self.children = {}  # Child nodes stored as {move: child_node}
        self.q_values = {}  # Q values for state transitions (s, s')
        self.n_values = {}  # N values for state transitions (s, s')
        self.p_values = {}  # P values for state transitions (s, s')
        self.w_values = {}  # W values for state transitions (s, s')
        self.parent = None  # Reference to the parent node

    def is_fully_expanded(self):
        return len(self.available_moves) == len(self.children)

    def select_child(self, c=np.sqrt(2)):
        best_child = None
        best_score = float("-inf")

        for move in self.available_moves:
            if move not in self.children:
                continue

            n = self.n_values.get(move, 0)
            if n == 0:
                return move

            q = self.q_values.get(move, 0)
            p = self.p_values.get(move, 0)

            exploration_term = c * p * (np.sqrt(np.log(self.n_values[self.state])) / (1 + n))
            score = q + exploration_term

            if score > best_score:
                best_score = score
                best_child = move

        return best_child




class PlayerAgent:

    def __init__(self, player, game_engine, eval_server_conn):
        self.player = player
        self.game_engine = game_engine
        self.eval_server_conn = eval_server_conn

    def get_next_move(self, available_moves, game_state):
        root_node = MCTSNode(game_state, available_moves)

        for _ in range(MAX_SIMULATIONS):
            node = root_node
            game_state_copy = game_state.copy()

            # Selection phase
            while not node.is_fully_expanded():
                move = node.select_child()
                game_state_copy = self.game_engine.model.generate_next_state(game_state_copy, move)
                if move not in node.children:
                    node.children[move] = MCTSNode(game_state_copy, available_moves)
                    node.children[move].parent = node  # Set the parent reference

            # Expansion phase
            unexplored_moves = [move for move in available_moves if move not in node.children]
            if unexplored_moves:
                move_to_expand = random.choice(unexplored_moves)
                game_state_copy = self.game_engine.model.generate_next_state(game_state_copy, move_to_expand)
                node.children[move_to_expand] = MCTSNode(game_state_copy, available_moves)
                node.children[move_to_expand].parent = node  # Set the parent reference

            # Simulation phase using the evaluator
            sim_result = self.evaluate_simulation(game_state_copy)

            # Determine the winning player (for example, if game_state_copy contains the winning player)
            winning_player = game_state_copy["current_player"]

            # Backpropagation phase
            while node is not None:
                move = move_to_expand  # For backpropagation, we use the expanded move
                node.n_values[move] = node.n_values.get(move, 0) + 1

                # Update rewards based on the winning player
                if self.player.name == winning_player:
                    node.w_values[move] = node.w_values.get(move, 0) + sim_result  # +1 reward for the winning player
                else:
                    node.w_values[move] = node.w_values.get(move, 0) - sim_result # -1 reward for all other players

                # Update Q-values for the state transition (s, s')
                if node.parent is not None:
                    parent_move = move_to_expand
                    parent_state = game_state
                    node.q_values[(parent_state, game_state_copy)] = (node.w_values[move] + sim_result) / (node.n_values[move] + 1)

                node = node.parent

        # Choose the move with the highest UCB1 score
        best_move = max(available_moves, key=lambda move: root_node.w_values.get(move, 0))
        return best_move

    def evaluate_simulation(self, game_state):
        # Serialize the game state and send it to the evaluator for evaluation
        serialized_game_state = json.dumps(game_state)
        eval_result = self.eval_server_conn.root.evaluate(self.player.name, base64.b64encode(serialized_game_state.encode('utf-8')).decode('ascii'))
        return float(eval_result)

    def update_tree(self, move):
        for player_agent in self.player_agents:
            # Check if it's the current player or an opponent
            if player_agent.player.name == self.player.name:
                continue  # Skip the current player

            # For opponents, update their trees with the move
            player_agent.game_state_copy = player_agent.game_engine.model.generate_next_state(player_agent.game_state_copy, move)
            player_agent.root_node = MCTSNode(player_agent.game_state_copy, player_agent.available_moves)


class Actor:
    def __init__(self):
        self.train_server_conn = None
        self.eval_server_conn = None
        self.evaluator_process = None

    def initialize_game(self):
        # TODO: To remove bias can randomize the color of the players
        game_config = GameConfig([[LudoModel.RED, LudoModel.YELLOW], [LudoModel.GREEN, LudoModel.BLUE]])

        game_engine = Ludo(game_config)

        return game_config, game_engine

    def initialize_data_stores(self):
        # Initialize data stores for logging and other game-related data
        data_store = {
            "player_won": None,  # Initialize as None until a player wins
            "states": [],  # List of game state tensors
        }

        log = {
            "config": None,  # Game configuration dictionary
            "game": [],  # List of dictionaries for each game
            "player_won": None  # Initialize as None until a player wins
        }

        return data_store, log

    def play_game(self, game_config, game_engine, data_store, log):
        player_agents = [PlayerAgent(player, game_engine, self.eval_server_conn) for player in game_config.players]

        game_engine.reset()
        start_time = time.perf_counter()

        while not game_engine.state["game_over"]:
            # Selecting the currently active player
            current_agent = player_agents[game_engine.state["current_player"]]

            game_data = {"game_state": game_engine.model.get_state_jsonable(game_engine.state)}
            data_store["states"].append(game_engine.model.state_to_repr(game_engine.state).tolist())

            # Finding all possible moves available at the game state
            all_moves = game_engine.model.all_possible_moves(game_engine.state)

            # Accumulating the moves available on the current dice roll
            available_moves = None
            for m in all_moves:
                if m["roll"] == game_engine.state["dice_roll"]:
                    available_moves = m["moves"]
                    break

            # Using MCTS to get the best move
            best_move = current_agent.get_next_move(available_moves, game_engine.state)

            move_id = game_engine.state["last_move_id"]
            # Taking the turn on the engine
            game_engine.turn(best_move, game_engine.state["last_move_id"] + 1)

            # Updating the MCTS tree
            current_agent.update_tree(best_move)

            # Storing game data
            game_data["move"] = best_move
            game_data["move_id"] = move_id
            log["game"].append(game_data)

        game_data = {"game_state": game_engine.model.get_state_jsonable(game_engine.state), "move_id": len(log["game"]), "move": []}
        log["game"].append(game_data)
        data_store["states"].append(game_engine.model.state_to_repr(game_engine.state).tolist())
        end_time = time.perf_counter()

        print(f"Time taken: {end_time - start_time}")

        print("Game Moves:")
        for move_data in log["game"]:
            print(f"Player: {move_data['game_state']['current_player']}, Move id: {move_data['move_id']}, Move: {move_data['move']}")

        data_store["player_won"] = game_config.players.index(game_engine.winner) + 1
        log["config"] = game_config.get_dict()
        log["player_won"] = data_store["player_won"]

    def send_data_to_train_server(self, data_store, log):
        try:
            # Check if the training server connection is established
            if self.train_server_conn is None:
                print("Error: Training server connection is not established.")
                return
            self.train_server_conn.root.push_game_data(json.dumps(data_store), json.dumps(log))

        except Exception as e:
            print(f"Error while sending data to the training server: {str(e)}")

    def start(self):
        self.train_server_conn = rpyc.connect(TRAIN_SERVER_IP, TRAIN_SERVER_PORT)

        from evaluator import EvaluatorMain
        self.evaluator_process = multiprocessing.Process(target=EvaluatorMain.process_starter, args=(TRAIN_SERVER_IP, TRAIN_SERVER_PORT, EVALUATOR_PORT, EVALUATION_BATCH_SIZE), name="Evaluator")
        self.evaluator_process.start()
        self.eval_server_conn = rpyc.connect("localhost", EVALUATOR_PORT)

        with ThreadPoolExecutor(max_workers=NUM_GAMES) as executor:
            game = 0
            while game < NUM_GAMES:
                game_config, game_engine = self.initialize_game()
                self.eval_server_conn.root.on_game_start(json.dumps(game_config.get_dict()))
                data_store, log = self.initialize_data_stores()

                # Submit a game to the thread pool
                future = executor.submit(self.play_game, game_config, game_engine, data_store, log)

                # Wait for the game to complete
                future.result()

                self.eval_server_conn.root.on_game_end()
                self.send_data_to_train_server(data_store, log)

                game += 1

        executor.shutdown()

        # Close the connections and stop the evaluator process
        self.train_server_conn.close()
        self.eval_server_conn.close()
        if not self.evaluator_process:
            self.evaluator_process.terminate()

    def close(self, signal, frame):
        self.train_server_conn.close()
        self.eval_server_conn.close()
        if not self.evaluator_process:
            self.evaluator_process.terminate()

if __name__ == "__main__":
    try:
        actor = Actor()

        signal(SIGINT, actor.close)
        signal(SIGTERM, actor.close)

        actor.start()
        actor.close(0, 0)
    except Exception as e:
        print(f"Couldn't connect to the Train Server: {str(e)}")
