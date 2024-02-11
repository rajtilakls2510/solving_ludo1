import ludoc
import pprint
import time

try:
    config = ludoc.GameConfig([["red", "yellow"], ["green", "blue"]])
    model = ludoc.LudoModel(config=config)
    state = ludoc.State(config.n_players)

    state.set({"n_players": config.n_players, "game_over": False, "current_player": 1, "num_more_moves": 0, "dice_roll": [6, 1], "last_move_id": 0,
               "Player 0": {"R1": "P22", "R2": "P22", "R3": "RB3", "R4": "RH6", "Y1": "P3", "Y2": "P3", "Y3": "YB3", "Y4": "YH6"},
               "Player 1": {"B1": "BB1", "B2": "BH6", "B3": "BH6", "B4": "BH1", "G1": "GH3", "G2": "P6", "G3": "GH6", "G4": "GH3"},
               "all_blocks": [{"pawns": ["R1", "R2"], "pos": "P22", "rigid": False},
                              {"pawns": ["Y1", "Y2"], "pos": "P3", "rigid": True},
                              {"pawns": ["G1", "G4"], "pos": "GH3", "rigid": True}]
               })
    print(state.get())
    start = time.perf_counter_ns()
    #state = model.generate_next_state(state, [[['Y1', 'Y2'], 'P3', 'P6'], ['R1', 'P22', 'P23']])

    # print(state.get())

    moves = model.all_possible_moves(state)
    end = time.perf_counter_ns()
    print(f"Time {(end - start) / 1e6} ms")
    pprint.pprint(moves)
except Exception as e:
    print(e)