import base64
import pprint
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
from threading import Lock, Event
import ludoc
import sys
import rpyc
import json
import tensorflow as tf
import mcts

try:
    tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], enable=True)
except:
    # No GPU, no problem. Code will just run slow
    pass
np.set_printoptions(threshold=sys.maxsize)
""" This file contains stuff related to the web server which serves the ReactJS frontend """

app = Flask(__name__)
cors = CORS(app)
move_lock, create_lock = Lock(), Lock()
move_event, create_event = Event(), Event()
move_event.set()
create_event.set()
ludo: ludoc.Ludo = None
data_store = None
log = None
players = None
networks = {}

model_path = "2023_Nov_10_04_08_24_131652"


def simulation_schedule(move_id):
    if move_id <= 100:
        return 90 * move_id + 1000
    return 10_000

# TRAIN_SERVER_IP = "localhost"
# TRAIN_SERVER_PORT = 18861


# ============= APIs =======================

@app.route("/check_running_game", methods=["GET"])
def check_game():
    running = True
    create_event.wait()
    if ludo is None:
        running = False
    return jsonify({"running": running}), 200


@app.route("/reset", methods=["GET"])
def reset():
    global ludo, data_store, log, players, networks
    create_event.wait()
    ludo = None
    data_store = None
    log = None
    players = None
    networks = None
    gc.collect()
    return "Done", 200


def pull_network_architecture(players):
    """ This method sends back a dictionary of player networks
        Return:
            networks= {"Player 1": model, "Player 2": another model, ...}
    """
    # train_server_conn = rpyc.connect(TRAIN_SERVER_IP, TRAIN_SERVER_PORT, config={"sync_request_timeout": None})
    start = time.perf_counter()
    # network_list = train_server_conn.root.get_nnet_list()
    # print(f"Network Choice: {network_list[-1]}")
    # # Getting the latest nnet
    # serialized_model = json.loads(train_server_conn.root.get_nnet(network_list[-1]))
    # model = tf.keras.Model.from_config(serialized_model["config"])
    # params = serialized_model["params"]
    # for i in range(len(params)):
    #     params[i] = tf.io.parse_tensor(base64.b64decode(params[i]), out_type=tf.float32)
    # model.set_weights(params)

    model = tf.keras.models.load_model(model_path)

    networks = {}
    for p in players:
        networks[p] = model
    print(f"Pull time: {time.perf_counter() - start}")
    # train_server_conn.close()
    return networks


def softmax(a, temp=0.1):
    if temp == 0:
        temp += 0.1
    a = np.exp(a - np.max(a))
    return np.exp(a / temp) / np.sum(np.exp(a / temp))


@tf.function(reduce_retracing=True)
def eval(network, inputs):
    return network(inputs, training=False)[:, 0]


def evaluator(eq, player):
    # This function is run on a different thread which continuously evaluates states in the queue

    while not eq.stop:
        states, indices = eq.get_elems_pending(n_elems=1024)
        results = []
        if len(indices) > 0:
            results = eval(networks[player], tf.convert_to_tensor(states))
        #    results = [1.0] * len(indices)
        eq.set_elems_result(results, indices)


class Agent:
    def __init__(self, player_index, game_engine):
        self.player_index = player_index
        self.game_engine = game_engine

    def take_next_move(self):
        pass

    def get_mode(self):
        pass

    def move_taken(self, move):
        pass

    def stop(self):
        pass


class HumanAgent(Agent):
    def __init__(self, player_index, game_engine):
        super().__init__(player_index, game_engine)

    def get_mode(self):
        return "Human"


class AIAgent(Agent):

    def __init__(self, player_index, game_engine: ludoc.Ludo):
        super().__init__(player_index, game_engine)
        self.tree = mcts.MCTree(ludo.state, player_index)
        self.tree.expand_root(ludo.model)
        state = self.game_engine.state.get()
        self.tree.prune_root(state["dice_roll"])

    def take_next_move(self):
        """This function executes MCTS simulations and choses a move based on that"""
        # if len(available_moves) > 0:
        #     return random.choice(available_moves)
        # return [[]] # This is the signature for pass move

        state = self.game_engine.state.get()
        # Initializing Evaluation Resources

        self.eq = mcts.EvaluationQueue(length=10_000, config=self.game_engine.model.config)
        t1 = threading.Thread(target=evaluator, args=(self.eq, self.player_index))
        t1.start()

        print("Searching")
        # Searching
        start = time.perf_counter_ns()
        print("Max Depth:",
              self.tree.mcts(simulations=simulation_schedule(state["last_move_id"] + 1), model=self.game_engine.model, c_puct=3.0, n_vl=3, eq=self.eq, max_depth=1000))
        end = time.perf_counter_ns()
        print("Time:", (end - start) / 1e6, "ms")

        # Releasing Evaluation Resources
        self.eq.set_stop()
        t1.join()
        del self.eq
        print("Selecting move")

        # Selecting and taking move
        move_for_tree, move_for_engine, probs_list = self.tree.select_next_move(selection_temp=0.1)

        # start = time.perf_counter()
        # available_moves = []
        # for m in self.game_engine.all_possible_moves:
        #     if m["roll"] == state["dice_roll"]:
        #         available_moves = m["moves"]
        # if len(available_moves) > 0:
        #     next_states = []
        #     for move in available_moves:
        #         next_states.append(self.game_engine.model.generate_next_state(state, move))
        #     for s in next_states:
        #         s["current_player"] = self.player_index
        #     next_states = tf.stack([self.game_engine.model.state_to_repr(s) for s in next_states])
        #
        #     results = self.nnet(next_states, training=False)[:, 0]
        #     p = softmax(results, temp=0)
        #     # print(f"{self.player_index} {results} \n {p}")
        #     chosen_move = random.choices(available_moves, p)[0]
        #
        #     # Getting the top 10 moves and their probabilities for logging
        #     top_moves = []
        #     top_probs = tf.math.top_k(p, k=min(10, p.shape[0]))
        #     for i in top_probs.indices:
        #         top_moves.append({"move": available_moves[i], "prob": float(p[i]), "value": float(results[i])})
        #
        # else:
        #     chosen_move = [[]]
        #     top_moves = [{"move": [[]], "prob": 1.0}]
        #
        # end = time.perf_counter()
        # print(f"Overall time: {end - start}")
        # print(f"Chosen move: {chosen_move}")
        # time.sleep(1)
        top_moves = []
        print(f"AI Taking move: {move_for_engine} {move_for_tree} with move_id: {state['last_move_id'] + 1}")
        print(probs_list)
        take_move_inner(move_for_engine, state["last_move_id"] + 1, top_moves)

    def get_mode(self):
        return "AI"

    def move_taken(self, move):
        moves, offset = self.tree.get_root_moves_list()
        self.tree.take_move(offset + moves.index(move), self.game_engine.model)
        state = self.game_engine.state.get()
        self.tree.prune_root(state["dice_roll"])

    def stop(self):
        if self.eq:
            self.eq.set_stop()
            del self.eq


@app.route("/create_new_game", methods=["POST"])
def create_new_game():
    """ [{mode: "AI", colours: ["red", "yellow"]}, {mode: "Human", colours: ["blue", "green"]}] """
    global ludo, data_store, log, players, networks
    create_event.clear()
    create_lock.acquire()
    if ludo is None:
        r = request.get_json()
        colours = []
        for p in r:
            colours.append(p["colours"])

        # Initializing Game
        ludo_config = ludoc.GameConfig(colours)
        p = []
        for p1, p2 in zip(r, range(ludo_config.n_players)):
            if p1["mode"] == "AI":
                p.append(p2)

        ludo = ludoc.Ludo(ludo_config)
        networks = pull_network_architecture(p)
        # networks = {}
        # Creating players
        players = []
        for index, mode in enumerate(r):
            if mode["mode"] == "AI":
                # TODO: Change Network Player repr
                players.append(AIAgent(index, ludo))
            else:
                players.append(HumanAgent(index, ludo))

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
    create_event.set()
    create_lock.release()
    threading.Thread(target=players[ludo.state.get()["current_player"]].take_next_move).start()
    return jsonify(new_state), 200


def get_state_jsonable_dict():
    new_state = {}
    if ludo is not None:
        new_state = ludo.state.get_visualizer_repr(ludo.model.config)
        new_state["config"] = ludo.model.config.get()
        new_state["modes"] = [m.get_mode() for m in players]
        for roll in ludo.all_current_moves:
            if roll["roll"] == ludo.state.get()["dice_roll"]:
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
    if not move_event.is_set():
        return "Move is being taken", 500
    new_state = get_state_jsonable_dict()
    return jsonify(new_state), 200


def take_move_inner(move, move_id, top_moves):
    move_lock.acquire()
    move_event.clear()
    # print(f"Move_id: {move_id} received, state: {ludo.state} Move: {move}")
    if move_id == ludo.state.get()["last_move_id"] + 1:
        global data_store, log
        game_data = {"game_state": ludo.state.get_visualizer_repr(ludo.model.config)}
        # data_store["states"].append(ludo.model.state_to_repr(ludo.state).tolist())

        ludo.turn(move, move_id)
        print(ludo.state.get())
        # pprint.pprint(ludo.all_current_moves)

        game_data["move"] = move
        game_data["move_id"] = move_id - 1
        game_data["top_moves"] = top_moves
        log["game"].append(game_data)

        # Notify all players this move has been taken
        for player in players:
            player.move_taken(move)

        # If game is over, send the data to train_server
        if ludo.state.get()["game_over"]:
            game_data = {"game_state": ludo.state.get_visualizer_repr(ludo.model.config), "move_id": len(log["game"]),
                         "move": []}
            log["game"].append(game_data)
            # data_store["states"].append(ludo.model.state_to_repr(ludo.state).tolist())
            # data_store["player_won"] = ludo.model.config.players.index(ludo.winner) + 1
            log["config"] = ludo.model.config.get()
            log["player_won"] = ludo.winner
            try:
                train_server_conn = rpyc.connect(TRAIN_SERVER_IP, TRAIN_SERVER_PORT,
                                                 config={"sync_request_timeout": None})
                train_server_conn.root.push_game_data(json.dumps(data_store), json.dumps(log))
                train_server_conn.close()
            except:
                pass
        else:
            # If game is not over, switch to the next player
            threading.Thread(target=players[ludo.state.get()["current_player"]].take_next_move).start()
    move_lock.release()
    move_event.set()


@app.route("/take_move", methods=["POST"])
def take_move():
    move = request.get_json()
    print(move)
    take_move_inner(move["move"], move["move_id"], move["top_moves"])
    new_state = get_state_jsonable_dict()
    return jsonify(new_state), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=False, debug=True)
