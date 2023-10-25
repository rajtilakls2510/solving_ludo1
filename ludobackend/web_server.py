from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
from threading import Lock
from ludo import Ludo, GameConfig, LudoModel, Pawn, PawnBlock
import numpy
import sys
import rpyc
import json

numpy.set_printoptions(threshold=sys.maxsize)
""" This file contains stuff related to the web server which serves the ReactJS frontend """

app = Flask(__name__)
cors = CORS(app)
lock = Lock()
ludo = None

TRAIN_SERVER_IP = "172.26.1.159"
TRAIN_SERVER_PORT = 18861


# ============= APIs =======================

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


@app.route("/state", methods=["GET"])
def get_state():
    new_state = get_state_jsonable_dict()
    return jsonify(new_state), 200


@app.route("/take_move", methods=["POST"])
def take_move():
    move = request.get_json()
    # print(move)
    lock.acquire()
    ludo.turn(move["move"], move["move_id"])
    lock.release()
    new_state = get_state_jsonable_dict()
    return jsonify(new_state), 200


if __name__ == "__main__":
    ludo = Ludo(GameConfig([[LudoModel.RED, LudoModel.YELLOW], [LudoModel.GREEN, LudoModel.BLUE]]))
    #
    # ludo.state = {"game_over": False, "current_player": 1, "dice_roll": [2], "num_more_moves": 0, "last_move_id": 0,
    #               ludo.model.config.players[0].name: {"single_pawn_pos": {"R1": "RB1", "R2": "RH5", "R3": "RB3", "R4": "RB4", "Y1": "YB1", "Y2": "YB2", "Y3": "P40", "Y4": "P32"},
    #                                                   "block_pawn_pos": {}},
    #               ludo.model.config.players[1].name: {
    #                   "single_pawn_pos": {"G1": "GB1", "G2": "P38", "G3": "GB3", "G4": "P20", "B1": "P42", "B2": "BB2", "B3": "BB3", "B4": "P17"},
    #                   "block_pawn_pos": {}},
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
    # ludo.turn([[]], 1)
    # print(ludo.state)
    # print(ludo.model.all_possible_moves(ludo.state))
    # print(ludo.winner)
    # print(ludo.model.get_state_jsonable(ludo.state))
    # print(ludo.state, [{"roll": move["roll"], "moves": len(move["moves"])} for move in ludo.all_current_moves])
    # ludo.turn([['Y2', 'P30', 'P33']], 1)
    # print([move["moves"] for move in ludo.all_current_moves if move["roll"] == [6,6,1]][0])
    # print(ludo.all_current_moves)
    app.run(host="0.0.0.0", port=5000)
