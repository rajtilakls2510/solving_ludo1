import rpyc
from ludo import Ludo, GameConfig, LudoModel
from mcts_ludo import MCTSTree, MCTSNode, simulate_game, mcts_search
""" This file contains stuff related to actor and MCTS search """

TRAIN_SERVER_IP = "localhost"
TRAIN_SERVER_PORT = 18861
NUM_GAMES = 10

train_server_conn = None

class Actor:
    def __init__(self):
        self.train_server_conn = None

    def initialize_game(self):
        # TODO: To remove bias can randomize the color of the players
        game_config = GameConfig([[LudoModel.RED], [LudoModel.GREEN], [LudoModel.YELLOW], [LudoModel.BLUE]])

        game_engine = Ludo(game_config)

        return game_config, game_engine

    def pull_network_architecture(self):
        try:
            if self.train_server_conn is None:
                self.train_server_conn = rpyc.connect(TRAIN_SERVER_IP, TRAIN_SERVER_PORT)

            network_architectures = self.train_server_conn.root.get_nnet_list()

            return network_architectures

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

        # just reset the ludo engine



    def send_data_to_train_server(self, data_store, log):
        try:
            # Check if the training server connection is established
            if self.train_server_conn is None:
                print("Error: Training server connection is not established.")
                return

            # TODO: Define the format and structure of the data you want to send to the training server
            # For example, you can send game moves or any other relevant data from data_store
            # Replace the following lines with your actual data formatting and sending code.

            # Example: Sending game moves
            game_moves = data_store.get("game_moves", [])
            self.train_server_conn.root.receive_game_moves(game_moves)

            # Example: Sending other game-related data
            # data = data_store.get("key_name", default_value)
            # self.train_server_conn.root.receive_data(data)

            print("Data sent to the training server successfully.")

        except Exception as e:
            print(f"Error while sending data to the training server: {str(e)}")


    def start(self):
        game = 0
        while game < NUM_GAMES:
            game_config, game_engine = self.initialize_game()
            network_architecture = self.pull_network_architecture()
            data_store = self.initialize_data_stores()
            
            self.play_game(game_config, game_engine, network_architecture, data_store)
            
            self.send_data_to_train_server(data_store)
            
            game += 1

if __name__ == "__main__":
    """ Initialize some parameters and start generating games after contacting the training server """
    try:
        actor = Actor()
        actor.start()
    except Exception as e:
        print(f"Couldn't connect to the Train Server: {str(e)}")

