import copy
import os
import time
from signal import signal, SIGINT, SIGTERM
import rpyc
from ludo import Ludo, GameConfig, LudoModel
import json
import tensorflow as tf
import numpy as np
import random
import gc
import base64

TRAIN_SERVER_IP = "localhost"
TRAIN_SERVER_PORT = 18861
EVALUATOR_PORT = 18862
NUM_GAMES = 1
# EVALUATION_BATCH_SIZE = 1024
# MAX_WORKERS = 4
# N_VL = 3
# C_PUCT = 5
# NUM_SIMULATIONS = 4
SELECTION_TEMP = 0.5


def softmax(a, temp=0.1):
    if temp == 0:
        temp += 0.001
    return np.exp(a / temp) / np.sum(np.exp(a / temp))


class PlayerAgent:

    def __init__(self, player, game_engine, nnet):
        self.player = player
        self.game_engine = game_engine
        self.nnet = nnet

    @tf.function(
        input_signature=[tf.TensorSpec(shape=(None, 59, 21), dtype=tf.float32)])
    def predict(self, batch):
        return self.nnet(batch)

    def get_next_move(self, state):
        """This function executes MCTS simulations and choses a move based on that"""
        # if len(available_moves) > 0:
        #     return random.choice(available_moves)
        # return [[]] # This is the signature for pass move

        start = time.perf_counter()
        available_moves = []
        for m in self.game_engine.model.all_possible_moves(state):
            if m["roll"] == state["dice_roll"]:
                available_moves = m["moves"]
        if len(available_moves) > 0:
            next_states = []
            for move in available_moves:
                next_states.append(self.game_engine.model.generate_next_state(state, move))
            next_states = tf.stack([self.game_engine.model.state_to_repr(state) for state in next_states])
            results = self.predict(next_states)[:, 0]
            p = softmax(results, temp=SELECTION_TEMP)
            chosen_move = random.choices(available_moves, p)[0]
        else:
            chosen_move = [[]]

        end = time.perf_counter()
        # print(f"Overall time: {end - start}")
        # print(f"Chosen move: {chosen_move}")
        return chosen_move


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

    def pull_network_architecture(self, players):
        """ This method sends back a dictionary of player networks
            Return:
                networks= {"Player 1": model, "Player 2": another model, ...}
        """
        start = time.perf_counter()
        network_list = self.train_server_conn.root.get_nnet_list()
        network_choices = {players[0].name: network_list[-1]}
        for player in players[1:]: network_choices[player.name] = random.choice(network_list)

        networks = {}
        for player_name, choice in network_choices.items():
            serialized_model = json.loads(self.train_server_conn.root.get_nnet(choice))
            model = tf.keras.Model.from_config(serialized_model["config"])
            params = serialized_model["params"]
            for i in range(len(params)):
                params[i] = tf.io.parse_tensor(base64.b64decode(params[i]), out_type=tf.float32)
            model.set_weights(params)
            networks[player_name] = model
        print(f"Pull time: {time.perf_counter() - start}")
        return networks

    def play_game(self, game_config, game_engine, data_store, log):
        networks = self.pull_network_architecture(game_config.players)
        player_agents = [PlayerAgent(player, game_engine, networks[player.name]) for player in game_config.players]

        game_engine.reset()
        start_time = time.perf_counter()


        # Playing the game
        while not game_engine.state["game_over"]:
            # Selecting the currently active player
            self.current_agent = player_agents[game_engine.state["current_player"]]

            game_data = {"game_state": game_engine.model.get_state_jsonable(game_engine.state)}
            data_store["states"].append(game_engine.model.state_to_repr(game_engine.state).tolist())

            # Selecting move
            # print(f"Selecting move for player: {self.current_agent.player.name}")
            best_move = self.current_agent.get_next_move(game_engine.state)

            move_id = game_engine.state["last_move_id"]
            # Taking the turn on the engine
            game_engine.turn(best_move, game_engine.state["last_move_id"] + 1)

            # print(f"State: {game_engine.state}")

            # Storing game data
            game_data["move"] = best_move
            game_data["move_id"] = move_id
            # TODO: Add all moves and their selection probabilities in game_data
            log["game"].append(game_data)

        game_data = {"game_state": game_engine.model.get_state_jsonable(game_engine.state), "move_id": len(log["game"]),
                     "move": []}
        log["game"].append(game_data)
        data_store["states"].append(game_engine.model.state_to_repr(game_engine.state).tolist())
        end_time = time.perf_counter()

        print(f"Game Generation Time: {end_time - start_time}")

        # print("Game Moves:")
        # for move_data in log["game"]:
        #     print(
        #         f"Player: {move_data['game_state']['current_player']}, Move id: {move_data['move_id']}, Move: {move_data['move']}")

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
        game = 0
        while game < NUM_GAMES:
            print(f"Initializing game: {game}")
            game_config, game_engine = self.initialize_game()
            data_store, log = self.initialize_data_stores()
            print(f"Playing game: {game}")
            self.play_game(game_config, game_engine, data_store, log)
            print(f"Sending data to server for game: {game}")
            self.send_data_to_train_server(data_store, log)

            game += 1


    def close(self, signal, frame):

        if self.train_server_conn:
            self.train_server_conn.close()
        exit(0)


if __name__ == "__main__":
    """ Initialize some parameters and start generating games after contacting the training server """
    print(f"Actor Process started: {os.getpid()}")
    tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], enable=True)
    actor = Actor()
    # try:
    signal(SIGINT, actor.close)
    signal(SIGTERM, actor.close)

    actor.start()
    actor.close(0, 0)
    # except Exception as e:
    #     print(f"Some error occured: {str(e)}")
    #     traceback.print_exc()
    #     actor.close(0,0)