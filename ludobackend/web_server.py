import base64
import threading
import time
from copy import deepcopy
from pathlib import Path
import gc
import random
import requests
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from threading import Lock
from ludo import Ludo, GameConfig, LudoModel, Pawn, PawnBlock
import numpy
import sys
import rpyc
import json
import tensorflow as tf
try:
    tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], enable=True)
except:
    # No GPU, no problem. Code will just run slow
    pass
numpy.set_printoptions(threshold=sys.maxsize)
""" This file contains stuff related to the web server which serves the ReactJS frontend """

app = Flask(__name__)
cors = CORS(app)
lock = Lock()
ludo = None
data_store = None
log = None
players = None

TRAIN_SERVER_IP = "172.26.1.159"
TRAIN_SERVER_PORT = 18861


# ============= APIs =======================

@app.route("/check_running_game", methods=["GET"])
def check_game():
    running = True
    if ludo is None:
        running = False
    return jsonify({"running": running}), 200


@app.route("/reset", methods=["GET"])
def reset():
    global ludo, data_store, log, players
    ludo = None
    data_store = None
    log = None
    players = None
    gc.collect()
    return "Done", 200


def pull_network_architecture(players):
    """ This method sends back a dictionary of player networks
        Return:
            networks= {"Player 1": model, "Player 2": another model, ...}
    """
    train_server_conn = rpyc.connect(TRAIN_SERVER_IP, TRAIN_SERVER_PORT, config={"sync_request_timeout": None})
    start = time.perf_counter()
    network_list = train_server_conn.root.get_nnet_list()
    print(f"Network Choice: {network_list[-1]}")
    # Getting the latest nnet
    serialized_model = json.loads(train_server_conn.root.get_nnet(network_list[-1]))
    model = tf.keras.Model.from_config(serialized_model["config"])
    params = serialized_model["params"]
    for i in range(len(params)):
        params[i] = tf.io.parse_tensor(base64.b64decode(params[i]), out_type=tf.float32)
    model.set_weights(params)
    networks = {}
    for p in players:
        networks[p.name] = model
    print(f"Pull time: {time.perf_counter() - start}")
    train_server_conn.close()
    return networks


def softmax(a, temp=0.1):
    if temp == 0:
        temp += 0.1
    a = np.exp(a - np.max(a))
    return np.exp(a / temp) / np.sum(np.exp(a / temp))


class Agent:
    def __init__(self, player_index, player, game_engine):
        self.player_index = player_index
        self.player = player
        self.game_engine = game_engine

    def take_next_move(self, state):
        pass


class HumanAgent(Agent):
    def __init__(self, player_index, player, game_engine):
        super().__init__(player_index, player, game_engine)


class AIAgent(Agent):

    def __init__(self, player_index, player, game_engine, nnet):
        super().__init__(player_index, player, game_engine)
        self.nnet = nnet

    def take_next_move(self, state):
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
            for state in next_states:
                state["current_player"] = self.player_index
            next_states = tf.stack([self.game_engine.model.state_to_repr(state) for state in next_states])

            results = self.nnet(next_states, training=False)[:, 0]
            p = softmax(results, temp=0)
            # print(f"{self.player_index} {results} \n {p}")
            chosen_move = random.choices(available_moves, p)[0]

            # Getting the top 10 moves and their probabilities for logging
            top_moves = []
            top_probs = tf.math.top_k(p, k=min(10, p.shape[0]))
            for i in top_probs.indices:
                top_moves.append({"move": available_moves[i], "prob": float(p[i]), "value": float(results[i])})

        else:
            chosen_move = [[]]
            top_moves = [{"move": [[]], "prob": 1.0}]

        end = time.perf_counter()
        # print(f"Overall time: {end - start}")
        # print(f"Chosen move: {chosen_move}")

        take_move_inner(chosen_move, state["last_move_id"] + 1, top_moves)


@app.route("/create_new_game", methods=["POST"])
def create_new_game():
    """ [{mode: "AI", colours: ["red", "yellow"]}, {mode: "Human", colours: ["blue", "green"]}] """
    global ludo, data_store, log, players
    if ludo is None:
        r = request.get_json()
        colours = []
        for p in r:
            colours.append(p["colours"])

        # Initializing Game
        ludo_config = GameConfig(colours)
        p = []
        for p1, p2 in zip(r, ludo_config.players):
            if p1["mode"] == "AI":
                p.append(p2)

        ludo = Ludo(ludo_config)
        networks = pull_network_architecture(p)

        # Creating players
        players = []
        for index, mode in enumerate(r):
            if mode["mode"] == "AI":
                players.append(AIAgent(index, ludo_config.players[index], ludo, networks[ludo_config.players[index].name]))
            else:
                players.append(HumanAgent(index, ludo_config.players[index], ludo))

        # Initializing stores
        data_store = {
            "player_won": None,  # Initialize as None until a player wins
            "states": [],  # List of game state tensors
        }

        log = {
            "config": None,  # Game configuration dictionary
            "game": [],  # List of dictionaries for each game
            "player_won": None  # Initialize as None until a player wins
        }

    new_state = get_state_jsonable_dict()
    threading.Thread(target=players[ludo.state["current_player"]].take_next_move, args=(ludo.state,)).start()
    return jsonify(new_state), 200


def get_state_jsonable_dict():
    new_state = {"config": ludo.model.config.get_dict()}
    pawns = {}
    positions = []
    for player in ludo.model.config.players:
        for pawn_id, pos in ludo.state[player.name]["single_pawn_pos"].items():
            pawns[pawn_id] = {"colour": ludo.model.get_colour_from_id(pawn_id), "blocked": False}
            positions.append({"pawn_id": pawn_id, "pos_id": pos})
        for block_id, pos in ludo.state[player.name]["block_pawn_pos"].items():
            for pawn in ludo.model.fetch_block_from_id(ludo.state, block_id).pawns:
                pawns[pawn.id] = {"colour": ludo.model.get_colour_from_id(pawn.id), "blocked": True}
                positions.append({"pawn_id": pawn.id, "pos_id": pos})
    new_state["game_over"] = ludo.state["game_over"]
    new_state["pawns"] = pawns
    new_state["positions"] = positions
    new_state["current_player"] = ludo.state["current_player"]
    new_state["dice_roll"] = ludo.state["dice_roll"]
    new_state["last_move_id"] = ludo.state["last_move_id"]
    new_state["num_more_moves"] = ludo.state["num_more_moves"]
    new_state["blocks"] = []
    new_state["moves"] = []
    for block in ludo.state["all_blocks"]:
        new_state["blocks"].append({"pawn_ids": [pawn.id for pawn in block.pawns], "rigid": block.rigid})
    for roll in ludo.all_current_moves:
        if roll["roll"] == ludo.state["dice_roll"]:
            new_state["moves"] = roll["moves"]
    return new_state


@app.route("/get_logs", methods=["GET"])
def get_logs():
    try:
        num = int(request.args.get('num_files'))
    except:
        num = 10
    train_server_conn = rpyc.connect(TRAIN_SERVER_IP, TRAIN_SERVER_PORT)
    filenames = json.loads(train_server_conn.root.get_log_filenames(num))
    train_server_conn.close()
    return jsonify(filenames)


@app.route("/get_log_file", methods=["GET"])
def get_log_file():
    run = request.args.get("run")
    file = request.args.get("file")
    train_server_conn = rpyc.connect(TRAIN_SERVER_IP, TRAIN_SERVER_PORT)
    content = json.loads(train_server_conn.root.get_log_file([run, "logs", file]))
    train_server_conn.close()
    return jsonify(content)


@app.route("/get_current_board", methods=["GET"])
def get_state():
    new_state = get_state_jsonable_dict()
    return jsonify(new_state), 200


def take_move_inner(move, move_id, top_moves):
    if move_id == ludo.state["last_move_id"] + 1:
        global data_store, log
        game_data = {"game_state": ludo.model.get_state_jsonable(ludo.state)}
        data_store["states"].append(ludo.model.state_to_repr(ludo.state).tolist())

        ludo.turn(move, move_id)

        game_data["move"] = move
        game_data["move_id"] = move_id
        game_data["top_moves"] = top_moves
        log["game"].append(game_data)

        # If game is over, send the data to train_server
        if ludo.state["game_over"]:
            game_data = {"game_state": ludo.model.get_state_jsonable(ludo.state), "move_id": len(log["game"]),
                         "move": []}
            log["game"].append(game_data)
            data_store["states"].append(ludo.model.state_to_repr(ludo.state).tolist())
            data_store["player_won"] = ludo.config.players.index(ludo.winner) + 1
            log["config"] = ludo.config.get_dict()
            log["player_won"] = data_store["player_won"]
            train_server_conn = rpyc.connect(TRAIN_SERVER_IP, TRAIN_SERVER_PORT, config={"sync_request_timeout": None})
            train_server_conn.root.push_game_data(json.dumps(data_store), json.dumps(log))
            train_server_conn.close()
        else:
            # If game is not over, switch to the next player
            threading.Thread(target=players[ludo.state["current_player"]].take_next_move, args=(ludo.state,)).start()


@app.route("/take_move", methods=["POST"])
def take_move():
    move = request.get_json()
    lock.acquire()
    take_move_inner(move["move"], move["move_id"], move["top_moves"])
    lock.release()
    new_state = get_state_jsonable_dict()
    return jsonify(new_state), 200


if __name__ == "__main__":
    # ludo = Ludo(GameConfig([[LudoModel.RED, LudoModel.YELLOW], [LudoModel.GREEN, LudoModel.BLUE]]))
    #
    # ludo.state = {"game_over":False,"current_player": 0, "dice_roll": [2], "num_more_moves":1, "last_move_id": 0,
    #                   ludo.model.config.players[0].name:
    #                       {"single_pawn_pos": {"R1": "RH6","R2": "P39","R3": "RH6","R4": "P35", "Y1": "YH6","Y2": "YH6","Y3": "YH6","Y4": "YH6",},
    #                                                 "block_pawn_pos": {}},
    #                   ludo.model.config.players[1].name: {
    #                       "single_pawn_pos": {"G1": "GH6", "G2": "P6", "G3": "GH6", "G4": "GB4", "B1": "BB1", "B2": "BH6","B3": "BH6","B4": "BH1"},
    #                       "block_pawn_pos": {}},
    #
    #               "all_blocks": [],
    #               }

    # ludo.state = {"game_over":False,"current_player": 3, "dice_roll": [1], "num_more_moves":0, "last_move_id": 0,
    #               ludo.model.config.players[0].name:
    #                   {"single_pawn_pos": {"R1": "RB1","R2": "RB2","R3": "RB3","R4": "RB4"},
    #                                             "block_pawn_pos": {}},
    #               ludo.model.config.players[1].name: {
    #                   "single_pawn_pos": {"G1": "GH6", "G2": "GB2", "G3": "P33", "G4": "P15"},
    #                   "block_pawn_pos": {}},
    #               ludo.model.config.players[2].name: {
    #                   "single_pawn_pos": {"Y1": "P42", "Y2": "P36", "Y3": "YB3", "Y4": "YB4"},
    #                   "block_pawn_pos": {}},
    #               ludo.model.config.players[3].name: {
    #                   "single_pawn_pos": {"B1": "BH6", "B2": "BH5", "B3": "BH6", "B4": "BH6"},
    #                   "block_pawn_pos": {}},
    #               "all_blocks": [
    # PawnBlock(
    #     [pawn for id in ["Y3", "Y4"] for pawn in ludo.model.pawns[ludo.model.get_colour_from_id(id)]
    #      if
    #      pawn.id == id],
    #     "BL0", rigid=True),
    #               ],
    #               }

    # ludo.state = {"game_over":False,"current_player": 1, "dice_roll": [1], "num_more_moves":0, "last_move_id": 0,
    #               ludo.model.config.players[0].name: {"single_pawn_pos": {"R1": "RH6","R2": "RH6","R4": "RH6", "Y1": "YH6", "Y2": "YH6","Y3": "YH6"},
    #                                             "block_pawn_pos": {"BL1": "P52"}},
    #               ludo.model.config.players[1].name: {
    #                   "single_pawn_pos": {"G1": "GH5", "G2": "GH6",  "G4": "GH6", "B1": "BH6","B2": "BH6",
    #                                       "B4": "BH6"},
    #                   "block_pawn_pos": {"BL0": "P13"}},
    #               "all_blocks": [
    #                   PawnBlock(
    #                       [pawn for id in ["G3", "B4"] for pawn in ludo.model.pawns[ludo.model.get_colour_from_id(id)]
    #                        if
    #                        pawn.id == id],
    #                       "BL0", rigid=True),
    #                   PawnBlock(
    #                       [pawn for id in ["R3", "Y4"] for pawn in ludo.model.pawns[ludo.model.get_colour_from_id(id)]
    #                        if
    #                        pawn.id == id],
    #                       "BL1", rigid=True),
    #               ],
    #               }
    # ludo.all_current_moves = ludo.model.all_possible_moves(ludo.state)
    # print(ludo.state)
    # print(ludo.all_current_moves)
    # ludo.turn([['R2', 'P39', 'P41']], 1)
    # print(ludo.state)
    # print(ludo.model.all_possible_moves(ludo.state))
    # print(ludo.winner)
    # print(ludo.model.get_state_jsonable(ludo.state))
    # print(ludo.state, [{"roll": move["roll"], "moves": len(move["moves"])} for move in ludo.all_current_moves])
    # ludo.turn([['Y2', 'P30', 'P33']], 1)
    # print([move["moves"] for move in ludo.all_current_moves if move["roll"] == [6,6,1]][0])
    # print(ludo.all_current_moves)
    app.run(host="0.0.0.0", port=5000, threaded=True)
