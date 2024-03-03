import argparse
import datetime
import json
import os
import random
import time
from pathlib import Path
import ludoc
import tensorflow as tf
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
# tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], enable=True)

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
        newest_checkpoint = config["evaluator"]["newest_checkpoint"]
        networks = [{"checkpoint": newest_checkpoint, "network": tf.keras.models.load_model(
            str(path / newest_checkpoint))}]
        self.current_newest_checkpoint = newest_checkpoint
        print(f'Newest Checkpoint Loaded: {newest_checkpoint}')
        best_checkpoint = config["actor"]["checkpoints"][config["actor"]["best_checkpoint_indices"][0]]
        for p in range(n_players-1):
            networks.append({"checkpoint": best_checkpoint, "network": tf.keras.models.load_model(str(path / best_checkpoint))})
            print(
                f'Checkpoint Loaded: {best_checkpoint}')
        return networks

    def play_game(self, game_engine, config):
        start_time = time.perf_counter()

        # Creating Players
        player_agents = [PlayerAgent(player, game_engine, networks[player]["network"]) for player in
                         range(game_engine.model.config.n_players)]

        # Resetting the engine
        game_engine.reset()

        log = {
            "config": None,  # Game configuration dictionary
            "game": [],  # List of dictionaries for each game
            "player_won": None,  # Initialize as None until a player wins
            "networks": [networks[player]["checkpoint"] for player in range(game_engine.model.config.n_players)] # List of networks that played that game
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
        end_time = time.perf_counter()
        print("")

        log["config"] = game_engine.model.config.get()
        log["player_won"] = game_engine.winner

        game_name = datetime.datetime.now().strftime('%Y_%b_%d_%H_%M_%S_%f')
        log_path = Path(config["root_path"]) / (config["log_store_subpath"]+"_evaluated")
        os.makedirs(log_path, exist_ok=True)
        with open(log_path / game_name, "w", encoding="utf-8") as f:
            f.write(json.dumps(log))

        print(f"Game Generation Time: {end_time - start_time}")
        return log["player_won"]

    def start(self, config_file):
        while True:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.loads(f.read())
               
            all_games = [datetime.datetime.strptime(dir, "%Y_%b_%d_%H_%M_%S_%f") for dir in os.listdir(Path(config["root_path"]) / config["experience_store_subpath"])]
            all_games.sort()
            if len(all_games) - config["evaluator"]["max_experience_store"] > 0:
                remove_games = all_games[:len(all_games) - config["evaluator"]["max_experience_store"]]
                for rm in remove_games:
                    try:
                        os.remove(Path(config["root_path"]) / config["experience_store_subpath"] / f"{rm.strftime('%Y_%b_%d_%H_%M_%S_%f')}.json")
                    except:
                        pass
               
            if not config["evaluator"]["evaluated"]:
                self.load_checkpoints(2, config)
                game = 0
                wins = 0
                while game < 200:
                    print(f"Initializing game: {game}")
                    game_engine = self.initialize_game()
                    print(f"Playing game: {game}")
                    player_won = self.play_game(game_engine, config)
                    if player_won == 0:
                        wins += 1
                    game += 1
                print([network["checkpoint"] for network in networks], wins)
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.loads(f.read())
                config["actor"]["checkpoints"].insert(0, self.current_newest_checkpoint)
                config["actor"]["checkpoints"] = config["actor"]["checkpoints"][:config["evaluator"]["max_checkpoints"]]
                best_indices = config["actor"]["best_checkpoint_indices"]
                if wins >= 110:
                    best_indices.insert(0, -1)
                config["actor"]["best_checkpoint_indices"] = [bi + 1 for i, bi in enumerate(best_indices) if i < 1]
                if config["evaluator"]["newest_checkpoint"] == self.current_newest_checkpoint:
                    config["evaluator"]["evaluated"] = True
                with open(config_file, "w", encoding="utf-8") as f:
                    f.write(json.dumps(config))
                
            else:
                print("Evaluator waiting for next checkpoint...")
                time.sleep(600)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path", type=str, default="train_config.json",
                        help="The config file that defines the configuration of the training run")
    args = parser.parse_args()
    config_file = args.config_path

    actor = Actor()
    actor.start(config_file)
