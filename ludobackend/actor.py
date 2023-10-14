import os
import time
import multiprocessing
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from signal import signal, SIGINT, SIGTERM
import rpyc
from ludo import Ludo, GameConfig, LudoModel
import json
from mcts import MCTNode, mcts_job, softmax
import numpy as np
import random
from copy import deepcopy
import gc

TRAIN_SERVER_IP = "localhost"
TRAIN_SERVER_PORT = 18861
EVALUATOR_PORT = 18862
NUM_GAMES = 1
EVALUATION_BATCH_SIZE = 1024
MAX_WORKERS = 4
N_VL = 3
C_PUCT = 5
NUM_SIMULATIONS = 420
SELECTION_TEMP = 1.0
PRIOR_TEMP = 1.0


def prune(node, roll):
    # Pruning all moves inconsistent with node
    from_index, to_index = 0, len(node.available_moves)
    found = False
    for index, move_dict in enumerate(node.available_moves):
        if move_dict["roll"] == roll and not found:
            from_index = index
            found = True
        elif move_dict["roll"] != roll and found:
            to_index = index
            found = False
            break
    node.prune(from_index, to_index)


class PlayerAgent:

    def __init__(self, player, game_engine):
        self.player = player
        self.game_engine = game_engine

    def get_next_move(self, root, evaluator_conn, threadpool, roll):
        """This function executes MCTS simulations and choses a move based on that"""
        # if len(available_moves) > 0:
        #     return random.choice(available_moves)
        # return [[]] # This is the signature for pass move

        # Run MCTS simulations
        start = time.perf_counter()
        futures = []
        for i in range(NUM_SIMULATIONS):
            futures.append(threadpool.submit(mcts_job, i, root, self.player, evaluator_conn, C_PUCT, N_VL, PRIOR_TEMP))
        max_depth = [future.result() for future in as_completed(futures)]
        end = time.perf_counter()
        print(f"Overall time: {end - start}")
        
        # Prune just to be safe
        prune(root, roll)

        # Select a move
        chosen_move_index = np.random.choice(np.arange(len(root.available_moves)), p=softmax(root.stats[self.player.name]["N"], temp=SELECTION_TEMP))
        chosen_move = root.available_moves[chosen_move_index]["move"]

        return chosen_move, chosen_move_index, max_depth

    def update_tree(self, root, roll, move_index):
        # Take the move on the tree and free the rest of the tree that is not required
        root = root.children[move_index]
        root.parent = None
        # Prune all moves which are inconsistent with current roll
        if root.expanded:
            print("Pruning in update tree")
            prune(root, roll)
        gc.collect()
        print(f"Root Moves: {root.available_moves}")
        return root


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

        # Creating root
        root = MCTNode(deepcopy(game_engine.state), game_config.players, game_engine.model, None)
        # Expanding root
        root.expand()
        prune(root, game_engine.state["dice_roll"])

        # Playing the game
        while not game_engine.state["game_over"]:
            # Selecting the currently active player
            current_agent = player_agents[game_engine.state["current_player"]]

            game_data = {"game_state": game_engine.model.get_state_jsonable(game_engine.state)}
            data_store["states"].append(game_engine.model.state_to_repr(game_engine.state).tolist())

            # Finding all possible moves available at the game state
            # all_moves = game_engine.model.all_possible_moves(game_engine.state)
            #
            # # Accumulating the moves available on current dice roll
            # available_moves = None
            # for m in all_moves:
            #     if m["roll"] == game_engine.state["dice_roll"]:
            #         available_moves = m["moves"]
            #         break

            # Selecting a move using MCTS
            print(f"Selecting move for player: {current_agent.player.name}")
            best_move, best_move_index, max_depth = current_agent.get_next_move(root, self.eval_server_conn, self.executor, game_engine.state["dice_roll"])
            
            print(f"Max depth: {max_depth}")
            
            move_id = game_engine.state["last_move_id"]
            # Taking the turn on the engine
            game_engine.turn(best_move, game_engine.state["last_move_id"] + 1)

            print(f"State: {game_engine.state}")
            
            # Updating the MCTS tree
            root = current_agent.update_tree(root, game_engine.state["dice_roll"], best_move_index)

            # Storing game data
            game_data["move"] = best_move
            game_data["move_id"] = move_id
            # TODO: Add all moves and their selection probabilities in game_data
            log["game"].append(game_data)

        game_data = {"game_state": game_engine.model.get_state_jsonable(game_engine.state), "move_id": len(log["game"]), "move": []}
        log["game"].append(game_data)
        data_store["states"].append(game_engine.model.state_to_repr(game_engine.state).tolist())
        end_time = time.perf_counter()

        print(f"Game Generation Time: {end_time - start_time}")

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

        # Starting the Evaluator process in the background which evaluates the states in MCTS
        from evaluator import EvaluatorMain
        self.evaluator_process = multiprocessing.Process(target=EvaluatorMain.process_starter, args=(TRAIN_SERVER_IP, TRAIN_SERVER_PORT, EVALUATOR_PORT, EVALUATION_BATCH_SIZE), name="Evaluator")
        self.evaluator_process.start()

        # Connecting to the evaluator to avail its APIs
        connected = False
        while not connected:
            try:
                print("Trying to connect to Evaluator...")
                self.eval_server_conn = rpyc.connect("localhost", EVALUATOR_PORT)
                connected = True
            except:
                connected = False
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

        game = 0
        while game < NUM_GAMES:
            print(f"Initializing game: {game}")
            game_config, game_engine = self.initialize_game()
            self.eval_server_conn.root.on_game_start(json.dumps(game_config.get_dict()))
            data_store, log = self.initialize_data_stores()
            print(f"Playing game: {game}")
            self.play_game(game_config, game_engine, data_store, log)
            self.eval_server_conn.root.on_game_end()
            print(f"Sending data to server for game: {game}")
            self.send_data_to_train_server(data_store, log)

            game += 1

        self.executor.shutdown(wait=True)

    def close(self, signal, frame):
        if self.executor:
            self.executor.shutdown(wait=True, cancel_futures=True)
        if self.train_server_conn:
            self.train_server_conn.close()
        if self.eval_server_conn:
            self.eval_server_conn.close()
        if self.evaluator_process:
            self.evaluator_process.terminate()
        exit(0)

if __name__ == "__main__":
    """ Initialize some parameters and start generating games after contacting the training server """
    print(f"Actor Process started: {os.getpid()}")
    actor = Actor()
    # try:
    signal(SIGINT, actor.close)
    signal(SIGTERM, actor.close)

    actor.start()
    actor.close(0,0)
    # except Exception as e:
    #     print(f"Some error occured: {str(e)}")
    #     traceback.print_exc()
    #     actor.close(0,0)