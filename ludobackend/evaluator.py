import base64
import json
import os
import threading
import random
import rpyc
from rpyc.utils.helpers import classpartial
from rpyc.utils.server import ThreadedServer
from signal import signal, SIGINT, SIGTERM
import tensorflow as tf
from queue import Queue


class QElem:
    def __init__(self, state_pair, event):
        self.state_pair = state_pair
        self.result = None
        self.is_evaluated = False
        self.trigger_to_check_all_complete = event


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
        elems = []
        for state_pair in tf.io.parse_tensor(base64.b64decode(state_pairs), out_type=tf.float32):
            elems.append(QElem(state_pair, trigger_event))
        for elem in elems:
            self.eval_object.queues[player_name].put(elem)

        all_complete = False
        while not all_complete:
            trigger_event.wait()
            for elem in elems:
                all_complete = all_complete and elem.is_evaluated
            trigger_event.clear()

        return base64.b64encode(
            tf.io.serialize_tensor(tf.stack([elem.result for elem in elems])).numpy()).decode('ascii')


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

    def pull_network_architecture(self, players):
        """ This method sends back a dictionary of player networks
            Return:
                networks= {"Player 1": model, "Player 2": another model, ...}
        """

        try:
            network_list = self.train_server_conn.root.get_nnet_list()
            network_choices = {players[0].name: network_list[-1]}
            for player in players[1:]: network_choices[player.name] = random.choice(network_list)

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
                    elems = []
                    while queue.qsize() > 0 and i < self.batch_size:
                        elems.append(queue.get())
                        i += 1

                    results = self.predict(self.networks[player["name"]], tf.stack(elems))

                    triggers_to_be_sent = []
                    for elem, result in zip(elems, results):
                        elem.result = result[0]
                        elem.is_evaluated = True
                        if elem.trigger_to_check_all_complete not in triggers_to_be_sent:
                            triggers_to_be_sent.append(elem.trigger_to_check_all_complete)

                    for trigger in triggers_to_be_sent:
                        trigger.set()
            self.evaluation_complete_event.set()

    @classmethod
    def process_starter(cls, train_server_ip, train_server_port, evaluator_port, evaluation_batch_size):
        print(f"Evaluator Process started PID: {os.getpid()}")

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