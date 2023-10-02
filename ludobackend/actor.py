import rpyc
from ludo import Ludo, GameConfig, LudoModel
import json
from copy import deepcopy
import random
import base64
import tensorflow as tf

TRAIN_SERVER_IP = "localhost"
TRAIN_SERVER_PORT = 18861
NUM_GAMES = 1

class PlayerAgent:
    def __init__(self, player_color, game_engine):
        self.player_color = player_color
        self.game_engine = game_engine

    def take_turn(self, available_moves, game_state):
        if available_moves:
            selected_move = random.choice(available_moves)
            self.game_engine.turn(selected_move, game_state["last_move_id"])

class Actor:
    def __init__(self):
        self.train_server_conn = None

    def initialize_game(self):
        # TODO: To remove bias can randomize the color of the players
        game_config = GameConfig([[LudoModel.RED], [LudoModel.GREEN], [LudoModel.YELLOW], [LudoModel.BLUE]])

        game_engine = Ludo(game_config)

        return game_config, game_engine

    def pull_network_architecture(self, config):
        """ This method sends back a dictionary of player networks
            Return:
                networks= {"Player 1": model, "Player 2": another model, ...}
        """

        try:
            network_list = self.train_server_conn.root.get_nnet_list()

            # TODO: Choose a network (from network_list) for each player in config object
            network_choices = {}
            for player in config.players: network_choices[player.name] = "some_model" # Dummy

            networks = {}
            for player_name, choice in network_choices.items():
                serialized_model = json.loads(self.train_server_conn.root.get_nnet(choice))
                model = tf.keras.Model.from_config(serialized_model["config"])
                params = serialized_model["params"]
                for i in range(len(params)):
                    params[i] = tf.io.parse_tensor(base64.b64decode(params[i]), out_type=tf.float32)
                model.set_weights(params)
                networks[player_name] = model
            return networks

        except Exception as e:
            print(f"Error while pulling network architectures: {str(e)}")
            return None

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

    def create_player_agent(self, player_color, game_engine):
        return PlayerAgent(player_color, game_engine)
    
    #TODO: make 4 different agents, only the current agent in play works on its mtcs search. 
    # generate random games for now

    def play_game(self, game_config, game_engine, network_architecture, data_store, log):
        players = [LudoModel.RED, LudoModel.GREEN, LudoModel.YELLOW, LudoModel.BLUE]
        player_agents = {}

        for player_color in players:
            player_agents[player_color] = self.create_player_agent(player_color, game_engine)

        current_player_index = 0

        #TODO: is_game_over in game_engine
        while not game_engine.is_game_over():
            current_player = players[current_player_index]
            game_state_copy = deepcopy(game_engine.state)

            if current_player in network_architecture:
                current_agent = player_agents[current_player]

                all_moves = game_engine.model.all_possible_moves(game_state_copy)

                if all_moves:
                    random_move = random.choice(all_moves)
                    best_move = random_move["moves"]
                else:
                    best_move = None

                current_agent.take_turn(all_moves, game_state_copy)

                if best_move:
                    game_data = {
                        "player": current_player + 1,
                        "move": best_move,
                        "game_state": game_engine.model.get_state_jsonable(game_state_copy)
                    }
                    log["game"].append(game_data)


            current_player_index = (current_player_index + 1) % len(players)

        print("Game Moves:")
        for move_data in log["game"]:
            print(f"Player: {move_data['player']}, Move: {move_data['move']}")

        data_store["player_won"] = game_engine.state["current_player"] + 1
        data_store["states"].append(game_engine.model.state_to_repr(game_state_copy).tolist())
        log["config"] = game_engine.model.get_dict()
        log["player_won"] = data_store["player_won"]

        game_engine.reset()

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
            game_config, game_engine = self.initialize_game()
            network_architecture = self.pull_network_architecture(game_config)
            data_store, log = self.initialize_data_stores()

            self.play_game(game_config, game_engine, network_architecture, data_store, log)

            self.send_data_to_train_server(data_store, log)

            game += 1

if __name__ == "__main__":
    """ Initialize some parameters and start generating games after contacting the training server """
    try:
        actor = Actor()
        actor.start()
    except Exception as e:
        print(f"Couldn't connect to the Train Server: {str(e)}")