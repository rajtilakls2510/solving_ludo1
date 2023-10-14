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

"""This file contains stuff related to the evaluator which runs in the background of actor to perform neural network evaluations"""


class QElem:
    """Objects of this class are stored in NNet queues for evaluation"""
    def __init__(self, states, event):
        self.states = states    # The states to evaluate
        self.result = tf.zeros(shape=(self.states.shape[0],)) # The results of their evaluation
        self.trigger_to_check_all_complete = event  # An event object to check whether all states have been evaluated or not
        self.total = self.states.shape[0]
        self.eval_start = self.eval_end = 0     # From which state index to which state index are currently being evaluated
        self.batch_start = self.batch_end = 0   # From which index to which index does the current evaluation lie in a batch

    def is_evaluated(self):
        return self.eval_end == self.states.shape[0]

    def set_result(self, result):
        # When the evaluation results for a particular subset of states comes, store the results
        elem_result = tf.reshape(result[self.batch_start: self.batch_end], shape=(-1, ))
        self.result = self.result + tf.pad(elem_result, [[self.eval_start, self.total - self.eval_end]])


@rpyc.service
class EvaluatorService(rpyc.Service):
    """This class serves the actor with the necessary APIs to get the evaluations for its states done"""

    def __init__(self, eval_object):
        self.eval_object = eval_object

    @rpyc.exposed
    def on_game_start(self, game_config):
        """This method is used by the actor to notify the evaluator a new game is starting and it should be prepared to evaluate requests"""
        players = json.loads(game_config)["players"]
        self.eval_object.setup_for_new_game(players)
        self.eval_object.main_event.set()

    @rpyc.exposed
    def on_game_end(self):
        """This method is used by the actor to notify the evaluator that the game has ended and it should pause all the evaluations"""
        self.eval_object.main_event.clear()
        self.eval_object.evaluation_complete_event.wait()

    @rpyc.exposed
    def evaluate(self, player_name, states):
        """This method is used to request an evaluation for a set of states.
            Arguments:
                - player_name: name of the player for whom the request is being evaluated
                - states: serialized tensor of shape (num_states, 59, 21)
            Return:
                - results: serialized tensor of shape (num_states,)
        """

        trigger_event = threading.Event()
        # Add the request to the NNet queue
        elem = QElem(tf.io.parse_tensor(base64.b64decode(states), out_type=tf.float32), trigger_event)
        self.eval_object.queues[player_name].put(elem)

        # Keep checking if all states are completely evaluated when triggered
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
        """This method setups up a new game by initializing its players and fetching their corresponding neural network architectures"""
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

    @tf.function(
    input_signature=[tf.TensorSpec(shape=(None, 59, 21), dtype=tf.float32)])
    def predict(self, batch):
        return self.model(batch)

    def evaluate(self):
        """This method continuously evaluates all requests present in the queue for each player"""
        while True:
            # Wait for game start notification from Actor
            self.main_event.wait()
            # Setup an event for notifying whether an evaluation is currently going on or completed
            self.evaluation_complete_event.clear()

            # For each player, get multiple requests to create one mini-batch and evaluate
            for player in self.players:
                queue = self.queues[player["name"]]
                if queue.qsize() > 0:
                    i = 0
                    state_batch = []
                    elems = []

                    # Pull multiple requests so that it fills one mini-batch and store a partially fulfilled request back in the queue for future evaluation
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
                        state_batch.append(elem.states[elem.eval_start : elem.eval_end])
                        i = batch_end
                    
                    self.model = self.networks[player["name"]]
                    # Evaluate a batch
                    results = self.predict(tf.concat(state_batch, axis=0))

                    # Collect all the triggers that have to be sent
                    triggers_to_be_sent = []
                    for elem in elems:
                        elem.set_result(results)
                        if elem.trigger_to_check_all_complete not in triggers_to_be_sent:
                            triggers_to_be_sent.append(elem.trigger_to_check_all_complete)

                    # Send the triggers to all requests to notify them that all of their states are evaluated
                    for trigger in triggers_to_be_sent:
                        trigger.set()
            time.sleep(0.000001)
            # Notify the on_game_end() method that the evaluator has successfully finished it's current batch and the game can end peacefully now
            self.evaluation_complete_event.set()

    @classmethod
    def process_starter(cls, train_server_ip, train_server_port, evaluator_port, evaluation_batch_size):
        print(f"Evaluator Process started PID: {os.getpid()}")
        tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], enable=True)
        signal(SIGINT, EvaluatorMain.process_terminator)
        signal(SIGTERM, EvaluatorMain.process_terminator)

        eval_object = EvaluatorMain.evaluator_main_object = EvaluatorMain(train_server_ip, train_server_port, evaluation_batch_size)

        # Start the Evaluator Server which serves Actor with NNet evaluations
        e_service = classpartial(EvaluatorService, eval_object)
        eval_object.eval_server = ThreadedServer(e_service, port=evaluator_port,
                                                protocol_config={'allow_public_attrs': True, })
        t1 = threading.Thread(target=eval_object.eval_server.start)
        t1.start()

        # Start the evaluations
        eval_object.evaluate()

    @classmethod
    def process_terminator(cls, signum, frame):
        eval_object = EvaluatorMain.evaluator_main_object
        eval_object.close()
        exit(0)

    def close(self):
        if self.train_server_conn:
            self.train_server_conn.close()
        self.eval_server.close()