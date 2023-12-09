import ludoc
import random
import time
import pprint

NUM_GAMES = 100

class PlayerAgent:

    def __init__(self, player, game_engine):
        self.player = player
        self.game_engine = game_engine

    def get_next_move(self, state: dict):
        """This function executes MCTS simulations and choses a move based on that"""

        # start = time.perf_counter()
        available_moves = []
        for m in self.game_engine.all_current_moves:
            if m["roll"] == state["dice_roll"]:
                available_moves = m["moves"]
        if len(available_moves) > 0:
            chosen_move = random.choices(available_moves, k=1)[0]
        else:
            chosen_move = [[]]
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

    def play_game(self, game_engine):
        player_agents = [PlayerAgent(player, game_engine) for player in
                         range(game_engine.model.config.n_players)]

        game_engine.reset()
        start_time = time.perf_counter()
        log = {
            "config": None,  # Game configuration dictionary
            "game": [],  # List of dictionaries for each game
            "player_won": None  # Initialize as None until a player wins
        }

        # Playing the game
        i = 0
        game_state_dict = game_engine.state.get()
        while not game_state_dict["game_over"] and i <= 1000:
            i += 1
            # print("|", end="")

            # Selecting the currently active player
            self.current_agent = player_agents[game_state_dict["current_player"]]

            game_data = {"game_state": game_engine.model.get_state_jsonable(game_engine.state)}
            # data_store["states"].append(game_engine.model.state_to_repr(game_engine.state).tolist())

            # Selecting move
            # print(f"Selecting move for player: {self.current_agent.player}")
            best_move, top_moves = self.current_agent.get_next_move(game_state_dict)
            # print(f"Selected move: {best_move}")

            move_id = game_state_dict["last_move_id"]
            # Taking the turn on the engine
            game_engine.turn(best_move, game_state_dict["last_move_id"] + 1)

            # Storing game data
            game_data["move"] = best_move
            game_data["move_id"] = move_id
            game_data["top_moves"] = top_moves
            log["game"].append(game_data)

            game_state_dict = game_engine.state.get()

        game_data = {"game_state": game_engine.model.get_state_jsonable(game_engine.state), "move_id": len(log["game"]),
                     "move": []}
        log["game"].append(game_data)
        # data_store["states"].append(game_engine.model.state_to_repr(game_engine.state).tolist())
        end_time = time.perf_counter()
        print("")

        # data_store["player_won"] = game_config.players.index(game_engine.winner) + 1
        log["config"] = game_engine.model.config.get()
        log["player_won"] = game_engine.winner
        # print(log)
        print("Length",len(log["game"]))
        print("Won:", log["player_won"])
        print(f"Game Generation Time: {end_time - start_time}")

    def start(self):

        game = 0
        while game < NUM_GAMES:
            print(f"Initializing game: {game}")
            game_engine = self.initialize_game()
            print(f"Playing game: {game}")
            self.play_game(game_engine)
            game += 1

if __name__ == "__main__":
    actor = Actor()
    actor.start()