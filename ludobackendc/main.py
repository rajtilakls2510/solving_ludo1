import ludoc

try:
    config = ludoc.GameConfig([["red", "yellow"], ["green", "blue"]])
    model = ludoc.LudoModel(config=config)
    # print(model.config)
    state = ludoc.State(config=config)

    state.set({"game_over": False, "current_player": 0, "num_more_moves": 1, "dice_roll": [6, 2], "last_move_id": 0,
               "Player 0": {"R1": "RB1", "R2": "P5", "R3": "P46", "R4": "RH6", "Y1": "YB4", "Y2": "P2", "Y3": "P30", "Y4": "P30"},
               "Player 1": {"B1": "BB1", "B2": "P6", "B3": "P47", "B4": "BH5", "G1": "GH1", "G2": "P3", "G3": "P31", "G4": "P31"},
               "all_blocks": [{"pawns": ["Y3", "Y4"], "pos": "P30", "rigid": False},
                              {"pawns": ["G3", "G4"], "pos": "P31", "rigid": True}]
               })
    print(state.get())
except Exception as e:
    print(e)