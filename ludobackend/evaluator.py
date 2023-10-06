import base64
import json
import os
import threading
import random
import time
import rpyc
from rpyc.utils.helpers import classpartial
from rpyc.utils.server import ThreadedServer
from signal import signal, SIGINT, SIGTERM
import tensorflow as tf
from queue import Queue


class QElem:
    def __init__(self, state_pairs, event):
        self.state_pairs = state_pairs
        self.result = tf.zeros(shape=(self.state_pairs.shape[0],))
        self.trigger_to_check_all_complete = event
        self.total = self.state_pairs.shape[0]
        self.eval_start = self.eval_end = 0
        self.batch_start = self.batch_end = 0

    def is_evaluated(self):
        return self.eval_end == self.state_pairs.shape[0]

    def set_result(self, result):
        elem_result = tf.reshape(result[self.batch_start: self.batch_end], shape=(-1, ))
        self.result = self.result + tf.pad(elem_result, [[self.eval_start, self.total - self.eval_end]])


@rpyc.service
class EvaluatorService(rpyc.Service):

    def __init__(self, eval_object):
        self.eval_object = eval_object

    @rpyc.exposed
    def on_game_start(self, game_config):
        players = json.loads(game_config)["players"]
        self.eval_object.setup_for_new_game(players)
        self.eval_object.main_event.set()

    @rpyc.exposed
    def on_game_end(self):
        self.eval_object.main_event.clear()
        self.eval_object.evaluation_complete_event.wait()

    @rpyc.exposed
    def evaluate(self, player_name, state_pairs):
        """This method is used to request an evaluation for a set of state_pairs.
            Arguments:
                - player_name: name of the player for whom the request is being evaluated
                - state_pairs: serialized tensor of shape (num_pairs, 59, 42)
            Return:
                - results: serialized tensor of shape (num_pairs,)
        """
        trigger_event = threading.Event()
        elem = QElem(tf.io.parse_tensor(base64.b64decode(state_pairs), out_type=tf.float32), trigger_event)
        self.eval_object.queues[player_name].put(elem)

        all_complete = False
        while not all_complete:
            trigger_event.wait()
            all_complete = elem.is_evaluated()
            trigger_event.clear()

        return base64.b64encode(
            tf.io.serialize_tensor(elem.result).numpy()).decode('ascii')


class EvaluatorMain:

    evaluator_main_object = None

    def __init__(self, train_server_ip, train_server_port, evaluation_batch_size):
        self.train_server_conn = rpyc.connect(train_server_ip, train_server_port)
        self.eval_server = None
        self.main_event = threading.Event()
        self.evaluation_complete_event = threading.Event()
        self.queues = {}
        self.batch_size = evaluation_batch_size

    def setup_for_new_game(self, players):
        self.players = players
        self.queues = {}
        for player in self.players:
            self.queues[player["name"]] = Queue()
        self.networks = self.pull_network_architecture(self.players)
        print(self.networks)

    def pull_network_architecture(self, players):
        """ This method sends back a dictionary of player networks
            Return:
                networks= {"Player 1": model, "Player 2": another model, ...}
        """
        start = time.perf_counter()
        network_list = self.train_server_conn.root.get_nnet_list()
        network_choices = {players[0]["name"]: network_list[-1]}
        for player in players[1:]: network_choices[player["name"]] = random.choice(network_list)

        networks = {}
        for player_name, choice in network_choices.items():
            serialized_model = json.loads(self.train_server_conn.root.get_nnet(choice))
            model = tf.keras.Model.from_config(serialized_model["config"])
            params = serialized_model["params"]
            for i in range(len(params)):
                params[i] = tf.io.parse_tensor(base64.b64decode(params[i]), out_type=tf.float32)
            model.set_weights(params)
            networks[player_name] = model
        print(f"Pull time: {time.perf_counter() - start}")
        return networks


    @tf.function
    def predict(self, model, batch):
        # TODO: Figure out input_signatures
        return model(batch)

    def evaluate(self):
        while True:
            self.main_event.wait()
            self.evaluation_complete_event.clear()
            for player in self.players:
                queue = self.queues[player["name"]]
                if queue.qsize() > 0:
                    i = 0
                    state_pair_batch = []
                    elems = []
                    while queue.qsize() > 0 and i < self.batch_size:
                        elem = queue.get()
                        if elem not in elems:
                            elems.append(elem)
                        batch_start = i
                        eval_start = elem.eval_end
                        if batch_start + (elem.total - elem.eval_end) > self.batch_size:
                            batch_end = self.batch_size
                            queue.put(elem)
                        else:
                            batch_end = batch_start + (elem.total - elem.eval_end)
                        eval_end = elem.eval_end + batch_end - batch_start

                        elem.batch_start, elem.batch_end, elem.eval_start, elem.eval_end = batch_start, batch_end, eval_start, eval_end
                        state_pair_batch.append(elem.state_pairs[elem.eval_start : elem.eval_end])
                        i = batch_end

                    results = self.predict(self.networks[player["name"]], tf.concat(state_pair_batch, axis=0))
                    triggers_to_be_sent = []
                    for elem in elems:
                        elem.set_result(results)
                        if elem.trigger_to_check_all_complete not in triggers_to_be_sent:
                            triggers_to_be_sent.append(elem.trigger_to_check_all_complete)

                    for trigger in triggers_to_be_sent:
                        trigger.set()
            time.sleep(0.001)
            self.evaluation_complete_event.set()

    @classmethod
    def process_starter(cls, train_server_ip, train_server_port, evaluator_port, evaluation_batch_size):
        print(f"Evaluator Process started PID: {os.getpid()}")
        tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], enable=True)
        signal(SIGINT, EvaluatorMain.process_terminator)
        signal(SIGTERM, EvaluatorMain.process_terminator)

        eval_object = EvaluatorMain.evaluator_main_object = EvaluatorMain(train_server_ip, train_server_port, evaluation_batch_size)

        e_service = classpartial(EvaluatorService, eval_object)
        eval_object.eval_server = ThreadedServer(e_service, port=evaluator_port,
                                                protocol_config={'allow_public_attrs': True, })
        t1 = threading.Thread(target=eval_object.eval_server.start)
        t1.start()

        eval_object.evaluate()

    @classmethod
    def process_terminator(cls, signum, frame):
        eval_object = EvaluatorMain.evaluator_main_object
        eval_object.close()
        exit(0)

    def close(self):
        self.train_server_conn.close()
        self.eval_server.close()