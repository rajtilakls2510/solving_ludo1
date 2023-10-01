import rpyc
from ludo import Ludo, GameConfig, LudoModel
# from mcts_ludo import MCTSTree, MCTSNode, simulate_game, mcts_search
import json
import base64
import tensorflow as tf
""" This file contains stuff related to actor and MCTS search """

TRAIN_SERVER_IP = "localhost"
TRAIN_SERVER_PORT = 18861
NUM_GAMES = 1


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
            "Player Won": index,
            "States": [] #game state tensor state_to_repr function in ludo model
        }

        return data_store


    def play_game(self, game_config, game_engine, network_architecture, data_store):
        players = [LudoModel.RED, LudoModel.GREEN, LudoModel.YELLOW, LudoModel.BLUE]
        
        #TODO: make 4 different agents, only the current agent in play works on its mtcs search. 
        # generate random games for now
        while not game_engine.is_game_over():
            # for current_player in players:
                game_state_copy = game_engine.copy_game_state()

                best_move = mcts_search(game_state_copy, num_simulations=1000)

                game_engine.apply_moves(current_player, [best_move])
                #TODO: from the turn function take the next player in play

                game_data = {
                    "player": current_player,
                    "move": best_move,
                    "game_state": game_engine.get_game_state()
                }
                data_store.append(game_data)

        print("Game Moves:")
        for move_data in data_store:
            print(f"Player: {move_data['player']}, Move: {move_data['move']}")

        # TODO: just reset the ludo engine



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
            data_store = self.initialize_data_stores()

            self.play_game(game_config, game_engine, network_architecture, data_store)

            self.send_data_to_train_server(data_store, log) # TODO: Implement log too

            game += 1

if __name__ == "__main__":
    """ Initialize some parameters and start generating games after contacting the training server """
    try:
        actor = Actor()
        actor.start()
    except Exception as e:
        print(f"Couldn't connect to the Train Server: {str(e)}")

