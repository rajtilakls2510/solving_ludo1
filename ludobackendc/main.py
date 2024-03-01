import ludoc
import pprint
import time
import numpy as np
import sys
import tensorflow as tf
np.set_printoptions(threshold=sys.maxsize)

try:
    config = ludoc.GameConfig([["red", "yellow"], ["green", "blue"]])
    # model = ludoc.LudoModel(config=config)
    game_engine = ludoc.Ludo(config)
    state = game_engine.state

    state.set({'n_players': 2, 'game_over': False, 'current_player': 0, 'num_more_moves': 0, 'dice_roll': [6,6,4],
               'last_move_id': 25,
               'Player 0': {'R1': 'P31', 'R2': 'RB2', 'R3': 'RB3', 'R4': 'RB4', 'Y2': 'YB2', 'Y3': 'YB3', 'Y1': 'P31',
                            'Y4': 'P32'},
               'Player 1': {'G2': 'GB2', 'G3': 'GB3', 'G4': 'GB4', 'B2': 'BB2', 'B3': 'BB3', 'B4': 'BB4', 'B1': 'P41',
                            'G1': 'P49'}, 'all_blocks': [{'pawns': ['Y1', 'R1'], 'pos': 'P31', 'rigid': True}]})
    print(game_engine.state.get_tensor_repr(config))
    start = time.perf_counter_ns()
    a = tf.convert_to_tensor(game_engine.model.get_next_states_tensor_reprs_and_moves(state)[0], dtype=tf.float32)
    end = time.perf_counter_ns()
    print(f"Time: {(end - start) / 1e3}")
    print(a.shape)
    # print(game_engine.model.get_next_states_tensor_reprs(state))
    # state.set({"n_players": config.n_players, "game_over": False, "current_player": 1, "num_more_moves": 0,
    #            "dice_roll": [6, 1], "last_move_id": 0,
    #            "Player 0": {"R1": "P22", "R2": "P22", "R3": "RB3", "R4": "RH6", "Y1": "P3", "Y2": "P3", "Y3": "YB3",
    #                         "Y4": "YH6"},
    #            "Player 1": {"B1": "BB1", "B2": "BH6", "B3": "BH6", "B4": "BH1", "G1": "GH3", "G2": "P6", "G3": "GH6",
    #                         "G4": "GH3"},
    #            "all_blocks": [{"pawns": ["R1", "R2"], "pos": "P22", "rigid": False},
    #                           {"pawns": ["Y1", "Y2"], "pos": "P3", "rigid": True},
    #                           {"pawns": ["G1", "G4"], "pos": "GH3", "rigid": True}]
    #            })
    # print(state.get_tensor_repr(config))
    # start = time.perf_counter_ns()
    # state = model.generate_next_state(state, [[['B3', 'B2'], 'P4', 'P7'], [['B3', 'B2'], 'P7', 'P9']])
    #
    # # print(state.get())
    #
    # moves = model.all_possible_moves(state)
    # end = time.perf_counter_ns()
    # print(f"Time {(end - start) / 1e6} ms")
    # pprint.pprint(moves)
except Exception as e:
    print(e)
