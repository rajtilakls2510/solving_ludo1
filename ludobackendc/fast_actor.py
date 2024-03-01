import datetime
import json
import os
from pathlib import Path
import numpy as np
import ludoc
import random
import time
import argparse
import tensorflow as tf
tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], True)

networks = []
@tf.function(reduce_retracing=True)
def eval(network, inputs):
    return network(inputs, training=False)[:, 0]


def move_probabilities(a, temp=0.1):
    if temp == 0:
        temp += 0.001
    return (a / temp) / tf.reduce_sum(a / temp)


class PlayerAgent:

    def __init__(self, player, game_engine, network):
        self.player = player
        self.game_engine = game_engine
        self.network = network

    def get_next_move(self, state_dict):

        # start = time.perf_counter()
        representations, available_moves = self.game_engine.model.get_next_states_tensor_reprs_and_moves(
            self.game_engine.state)
        if available_moves == []:
            chosen_move = [[]]
        else:

            next_values = eval(self.network, tf.convert_to_tensor(representations, dtype=tf.float32))
            temp = 0 if state_dict["last_move_id"] > 100 else 1
            if state_dict["last_move_id"] == 101:
                print("\\", end="")
            chosen_move = random.choices(available_moves, k=1, weights=move_probabilities(next_values, temp))[0]
        # end = time.perf_counter()
        # print(f"Overall time: {end - start}")
        # print(f"Chosen move: {chosen_move}")
        return chosen_move, []


class Actor:


    def initialize_game(self):
        # Removing bias by randomizing the color of the players

        colours = [["red", "yellow"], ["green", "blue"]]
        random.shuffle(colours)
        game_config = ludoc.GameConfig(colours)

        game_engine = ludoc.Ludo(game_config)

        return game_engine

    def load_checkpoints(self, n_players, config):
        global networks
        path = Path(config["root_path"]) / config["checkpoints_subpath"]
        if networks == []:
            best_checkpoint = config["actor"]["checkpoints"][config["actor"]["best_checkpoint_index"]]
            if self.current_best_checkpoint != best_checkpoint:
                networks = [tf.keras.models.load_model(
                    str(path / best_checkpoint))]
                print(f'Best Checkpoint Loaded: {best_checkpoint}')
                self.current_best_checkpoint = best_checkpoint
            for p in range(n_players-1):
                chosen_checkpoint = np.random.randint(low=0, high=len(config["actor"]["checkpoints"]), size=1)[0]
                networks.append(tf.keras.models.load_model(str(path / config["actor"]["checkpoints"][chosen_checkpoint])))
                print(
                    f'Checkpoint Loaded: {config["actor"]["checkpoints"][chosen_checkpoint]}')
        else:
            best_checkpoint = config["actor"]["checkpoints"][config["actor"]["best_checkpoint_index"]]
            if self.current_best_checkpoint != best_checkpoint:
                networks[0].set_weights(tf.keras.models.load_model(
                    str(path / best_checkpoint)).get_weights())
                print(f'Best Checkpoint Loaded: {best_checkpoint}')
                self.current_best_checkpoint = best_checkpoint

            for p in range(1, n_players):
                chosen_checkpoint = np.random.randint(low=0, high=len(config["actor"]["checkpoints"]), size=1)[0]
                networks[p].set_weights(
                    tf.keras.models.load_model(str(path / config["actor"]["checkpoints"][chosen_checkpoint])).get_weights())
                print(
                    f'Checkpoint Loaded: {config["actor"]["checkpoints"][chosen_checkpoint]}')

        return networks

    def play_game(self, game_engine, config_file):
        start_time = time.perf_counter()
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.loads(f.read())

        # Loading and choosing checkpoints to play with
        networks = self.load_checkpoints(game_engine.model.config.n_players, config)

        # Creating Players
        player_agents = [PlayerAgent(player, game_engine, networks[player]) for player in
                         range(game_engine.model.config.n_players)]

        # Resetting the engine
        game_engine.reset()

        log = {
            "config": None,  # Game configuration dictionary
            "game": [],  # List of dictionaries for each game
            "player_won": None  # Initialize as None until a player wins
        }
        data_store = {
            "player_won": None,
            "states": []
        }

        # Playing the game
        i = 0
        game_state_dict = game_engine.state.get()
        # print(game_state_dict)
        while not game_state_dict["game_over"] and i <= 1000:
            i += 1
            print("|", end="")

            # Selecting the currently active player
            self.current_agent = player_agents[game_state_dict["current_player"]]
            # print("For Player:", self.current_agent.player)

            game_data = {"game_state": game_engine.state.get_visualizer_repr(game_engine.model.config)}
            data_store["states"].append(game_engine.state.get_tensor_repr(game_engine.model.config).tolist())

            # Selecting move
            # print(f"Selecting move for player: {self.current_agent.player}")
            best_move, top_moves = self.current_agent.get_next_move(game_state_dict)
            # print(f"Selected move: {best_move}")

            move_id = game_state_dict["last_move_id"]
            # Taking the turn on the engine
            game_engine.turn(best_move, game_state_dict["last_move_id"] + 1)

            # # Storing game data
            game_data["move"] = best_move
            game_data["move_id"] = move_id
            game_data["top_moves"] = top_moves
            log["game"].append(game_data)

            game_state_dict = game_engine.state.get()
            # print(game_state_dict)

        game_data = {"game_state": game_engine.state.get_visualizer_repr(game_engine.model.config), "move_id": len(log["game"]),
                     "move": []}
        log["game"].append(game_data)
        data_store["states"].append(game_engine.state.get_tensor_repr(game_engine.model.config).tolist())
        end_time = time.perf_counter()
        print("")

        data_store["player_won"] = game_engine.winner + 1
        log["config"] = game_engine.model.config.get()
        log["player_won"] = game_engine.winner

        game_name = datetime.datetime.now().strftime('%Y_%b_%d_%H_%M_%S_%f')
        store_path = Path(config["root_path"]) / config["experience_store_subpath"]
        log_path = Path(config["root_path"]) / config["log_store_subpath"]
        os.makedirs(store_path, exist_ok=True)
        os.makedirs(log_path, exist_ok=True)
        with open(store_path / game_name, "w", encoding="utf-8") as f:
            f.write(json.dumps(data_store))
        with open(log_path / game_name, "w", encoding="utf-8") as f:
            f.write(json.dumps(log))

        print(f"Game Generation Time: {end_time - start_time}")

    def start(self, config_file):
        self.current_best_checkpoint = ""
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.loads(f.read())

        game = config["actor"]["initial_game"]
        while game < config["actor"]["final_game"]:
            print(f"Initializing game: {game}")
            game_engine = self.initialize_game()
            print(f"Playing game: {game}")
            self.play_game(game_engine, config_file)
            game += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path", type=str, default="train_config.json",
                        help="The config file that defines the configuration of the training run")
    args = parser.parse_args()
    config_file = args.config_path

    actor = Actor()
    actor.start(config_file)
