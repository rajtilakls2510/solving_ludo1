import time
import multiprocessing
from signal import signal, SIGINT, SIGTERM
import rpyc
from ludo import Ludo, GameConfig, LudoModel
import json
import random

TRAIN_SERVER_IP = "localhost"
TRAIN_SERVER_PORT = 18861
EVALUATOR_PORT = 18862
NUM_GAMES = 1
EVALUATION_BATCH_SIZE = 512


class PlayerAgent:

    def __init__(self, player, game_engine):
        self.player = player
        self.game_engine = game_engine

    def get_next_move(self, available_moves, game_state):

        # TODO: Write MCTS Search to find next move here
        if len(available_moves) > 0:
            return random.choice(available_moves)
        return [[]] # This is the signature for pass move

    def update_tree(self, move):
        # TODO: Take the move on the tree and free the rest of the tree that is not required
        pass


class Actor:
    def __init__(self):
        self.train_server_conn = None
        self.eval_server_conn = None
        self.evaluator_process = None

    def initialize_game(self):
        # TODO: To remove bias can randomize the color of the players
        game_config = GameConfig([[LudoModel.RED, LudoModel.YELLOW], [LudoModel.GREEN,LudoModel.BLUE]])

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
        player_agents = [PlayerAgent(player, game_engine) for player in game_config.players]

        game_engine.reset()
        start_time = time.perf_counter()

        while not game_engine.state["game_over"]:
            # Selecting the currently active player
            current_agent = player_agents[game_engine.state["current_player"]]

            game_data = {"game_state": game_engine.model.get_state_jsonable(game_engine.state)}
            data_store["states"].append(game_engine.model.state_to_repr(game_engine.state).tolist())

            # Finding all possible moves available at the game state
            all_moves = game_engine.model.all_possible_moves(game_engine.state)

            # Accumulating the moves available on current dice roll
            available_moves = None
            for m in all_moves:
                if m["roll"] == game_engine.state["dice_roll"]:
                    available_moves = m["moves"]
                    break

            # Selecting a move using MCTS (currently random)
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

        # TODO: Start thread pool

        game = 0
        while game < NUM_GAMES:
            game_config, game_engine = self.initialize_game()
            self.eval_server_conn.root.on_game_start(json.dumps(game_config.get_dict()))
            data_store, log = self.initialize_data_stores()

            self.play_game(game_config, game_engine, data_store, log)
            self.eval_server_conn.root.on_game_end()
            self.send_data_to_train_server(data_store, log)

            game += 1

        # TODO: Stop thread pool
        self.evaluator_process.terminate()

    def close(self, signal, frame):
        # TODO: Stop thread pool
        self.train_server_conn.close()
        self.eval_server_conn.close()
        if not self.evaluator_process:
            self.evaluator_process.terminate()

if __name__ == "__main__":
    """ Initialize some parameters and start generating games after contacting the training server """
    try:
        actor = Actor()

        signal(SIGINT, actor.close)
        signal(SIGTERM, actor.close)

        actor.start()
    except Exception as e:
        print(f"Couldn't connect to the Train Server: {str(e)}")