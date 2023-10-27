import base64
import json
import multiprocessing
import random
import gc
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
from signal import signal, SIGINT, SIGTERM
import datetime
import rpyc
import tensorflow as tf
import numpy as np
from queue import Queue
from rpyc import ThreadedServer
from tensorflow.keras.optimizers import serialize


""" This file contains only stuff related to the learner """

DIRECTORY = Path("runs")
TRAIN_DIRECTORY = DIRECTORY / "run2"
MIN_STORED_GAMES = 1_000   # The minimum number of stored games in experience store before which training can begin
BATCH_SIZE = 2048
NUM_FILES_TO_FETCH_BATCH = 8    # The number of files that need to be loaded to create one mini-batch.
MIN_NUM_JOBS = 2   # The recommended number of pre-fetched batches that should be in the queue when the learner consumes batches. Also, this is the number of threads in the ThreadPoolExecutor.
NUM_BATCHES = 1_00_000    # The total number of mini-batches to train on
INITIAL_BATCH = 0
SAVE_EVERY_BATCHES = 2_000     # Number of mini-batches of training before saving a checkpoint
PREFETCHER_PORT = 18890     # The port at which the Data Loader Server will run
SAVE_FOR_ELO_AFTER_TIME = 28_800 # Save a checkpoint for after every 8 hours for later Elo evaluation



# ========================== Pre-fetcher Process =======================================

@rpyc.service
class DataLoaderService(rpyc.Service):
    """This class serves the learner with the mini-batches and other requirements to control the data loader"""

    @rpyc.exposed
    def get_batch(self):
        """This function gets one mini-batch from the queue, serializes it and sends it to learner"""
        states, rewards = DataLoader.data_loader_object.get_batch()
        states = base64.b64encode(
            tf.io.serialize_tensor(states).numpy()).decode('ascii')
        rewards = base64.b64encode(
            tf.io.serialize_tensor(rewards).numpy()).decode('ascii')
        return json.dumps([states, rewards])

    @rpyc.exposed
    def get_qsize(self):
        """This functions returns the current queue size of the pre-fetch queue. If the queue size is zero, it means that the pre-fetcher is unable to push batches fast enough"""
        return DataLoader.data_loader_object.prefetch_queue.qsize()


class DataLoader:
    """ This is the main data loader class which loads mini-batches and pushes them to a queue whose contents are to be consumed by the learner """

    data_loader_object = None

    def __init__(self, min_num_jobs_in_queue=4, server=None):
        self.server = server

        # Initializing the thread pool executor which will handle fetching of batches from game files
        self.executor = ThreadPoolExecutor(max_workers=min_num_jobs_in_queue)

        # Pre-fetch queue stores all the batches that have been pre-fetched
        self.prefetch_queue = Queue()
        self.num_jobs = min_num_jobs_in_queue
        self.experience_store_path = TRAIN_DIRECTORY / "experience_store"

        # Adding some fetch jobs to fill the queue while the learner initializes it's training process
        for _ in range(self.num_jobs):
            self.executor.submit(self.fetch)

    @classmethod
    def process_starter(cls, prefetcher_port, min_num_jobs_in_queue):
        print(f"Pre-fetcher Process started PID: {os.getpid()}")

        signal(SIGINT, DataLoader.process_terminator)
        signal(SIGTERM, DataLoader.process_terminator)

        # Starting Data Loader server to server the requests from Main learner process
        server = ThreadedServer(DataLoaderService, port=prefetcher_port)
        t1 = threading.Thread(target=server.start)
        t1.start()

        DataLoader.data_loader_object = DataLoader(min_num_jobs_in_queue, server)

        # Continuously fetching batches from secondary storage and pushing it to pre-fetched queue
        DataLoader.data_loader_object.keep_fetching()

    def keep_fetching(self):
        while True:
            # Adding fetch jobs to the thread pool if there aren't enough jobs in queue
            for _ in range(min(self.num_jobs - self.executor._work_queue.qsize(), self.num_jobs - self.prefetch_queue.qsize())):
                self.executor.submit(self.fetch)
            time.sleep(0.0001)

    @classmethod
    def process_terminator(cls, signum, frame):
        if DataLoader.data_loader_object:
            DataLoader.data_loader_object.close()
        exit(0)

    def get_pawn_permutation(self):
        # This function returns the permutation matrix for one colour of pawns
        perm = np.zeros(shape=(4, 4))
        permuted_indices = np.random.permutation(4)
        for i in range(4):
            perm[i, permuted_indices[i]] = 1
        return perm

    def fetch(self):
        """ This function selects some files and fetches one mini-batch from those files and pushes the batch to the pre-fetch queue"""
        states = []
        rewards = []

        # Selecting some files randomly
        files = random.choices(os.listdir(self.experience_store_path), k=NUM_FILES_TO_FETCH_BATCH)

        # For every selected file, fetch part of the batch
        for file in files:

            # Load the whole file
            try:
                with open(self.experience_store_path / file, mode="r", encoding="utf-8") as f:
                    game_data = json.loads(f.read())
            except:
                # To maintain max store constraint if the train server has removed the file, read another file
                file = random.choice(os.listdir(self.experience_store_path))
                with open(self.experience_store_path / file, mode="r", encoding="utf-8") as f:
                    game_data = json.loads(f.read())

            # Find who won
            winner_player = game_data["player_won"]
            num_states = len(game_data["states"])

            # BATCH_SIZE // NUM_FILES_TO_FETCH_BATCH number of states must be selected
            for _ in range(BATCH_SIZE // NUM_FILES_TO_FETCH_BATCH):
                # Choose one state
                chosen_state = np.random.randint(low=0, high=num_states)
                state = np.array(game_data["states"][chosen_state])

                # Apply turn augmentation
                player = random.choice(np.arange(4) + 1)
                state[:, -1] = player

                # Apply pawn augmentation
                permutation_array = np.eye(N=21)
                permutation_array[:4, :4] = self.get_pawn_permutation()  # Red
                permutation_array[4:8, 4:8] = self.get_pawn_permutation()  # Green
                permutation_array[8:12, 8:12] = self.get_pawn_permutation()  # Yellow
                permutation_array[12:16, 12:16] = self.get_pawn_permutation()  # Blue
                state = state @ permutation_array

                # Select the appropriate reward based on who won
                reward = [1] if state[0, -1] == winner_player else [-1]

                states.append(state)
                rewards.append(reward)
        # Push the batch to the pre-fetch queue
        self.prefetch_queue.put((tf.convert_to_tensor(states, dtype=tf.float32), tf.convert_to_tensor(rewards, dtype=tf.float32)))

    def get_batch(self):
        return self.prefetch_queue.get()

    def close(self):
        if self.server:
            self.server.close()
        self.executor.shutdown(wait=True, cancel_futures=True)


# ========================== Learner Main Process =======================================


def check_enough_games():
    files = os.listdir(TRAIN_DIRECTORY / "experience_store")
    return len(files) >= MIN_STORED_GAMES


class Learner:

    def load_latest_checkpoint(self):
        CHKPT_DIRECTORY = TRAIN_DIRECTORY / "checkpoints"
        chkpt_names = [dir for dir in os.listdir(CHKPT_DIRECTORY) if len(dir.split(".")) == 1]
        chkpt_names.sort()
        latest_model = chkpt_names[-1]
        path = CHKPT_DIRECTORY / latest_model
        self.model = tf.keras.models.load_model(path)

        # Loading the optimizer and setting schedule
        try:

            with open(TRAIN_DIRECTORY / "checkpoints" / "optimizer.json", encoding="utf-8") as f:
                self.optimizer = tf.keras.optimizers.deserialize(json.loads(f.read()))
        except:
            self.optimizer = tf.keras.optimizers.Adam()
        boundaries = []
        values = []

        if INITIAL_BATCH < 2_00_000:
            boundaries.extend([2_00_000 - INITIAL_BATCH, 6_00_000 - INITIAL_BATCH])
            values.extend([1e-2, 1e-3, 1e-4])
        elif 2_00_000 <= INITIAL_BATCH < 6_00_000:
            boundaries.extend([6_00_000 - INITIAL_BATCH, ])
            values.extend([1e-3, 1e-4])
        else:
            values.extend([1e-4])
        lr_schedule = tf.keras.optimizers.schedules.PiecewiseConstantDecay(boundaries=boundaries,
                                                                           values=values)
        self.optimizer.learning_rate = lr_schedule
        print(f"Schedule Loaded: {boundaries} {values}")
        print(f"Loaded model {path}")

    @tf.function
    def train_step(self, x_batch, y_batch):
        with tf.GradientTape() as tape:
            y_pred = self.model(x_batch)
            l = self.loss(y_batch, y_pred)
            l += sum(self.model.losses)

        grads = tape.gradient(l, self.model.trainable_variables)
        self.optimizer.apply_gradients(zip(grads, self.model.trainable_variables))
        return l

    def start(self):

        # Creating a background process for Data Loading and pre-fetching
        self.data_loader_process = multiprocessing.Process(target=DataLoader.process_starter, args=(PREFETCHER_PORT, MIN_NUM_JOBS))
        self.data_loader_process.start()

        # Connecting to the Data Loader server to fetch mini-batches from
        connected = False
        while not connected:
            try:
                print("Trying to connect to Data Loader...")
                self.data_loader_conn = rpyc.connect("localhost", PREFETCHER_PORT, config={"sync_request_timeout": None})
                connected = True
            except:
                connected = False

        # Loading latest checkpoint and initializing necessary entities
        self.load_latest_checkpoint()
        self.loss = tf.keras.losses.MeanSquaredError()
        start = time.perf_counter()
        for i in range(INITIAL_BATCH, NUM_BATCHES):
            print(f"Batch: {i}. QSize: {self.data_loader_conn.root.get_qsize()}", end="")

            # Fetching and parsing a mini-batch of states from the data loader
            x_batch, y_batch = json.loads(self.data_loader_conn.root.get_batch())
            x_batch = tf.io.parse_tensor(base64.b64decode(x_batch), out_type=tf.float32)
            y_batch = tf.io.parse_tensor(base64.b64decode(y_batch), out_type=tf.float32)

            # Train pass using the batch
            l = self.train_step(x_batch, y_batch)

            print(f" Loss: {l.numpy()}")
            # TODO: Log loss for training

            # Logistics
            if (i+1) % SAVE_EVERY_BATCHES == 0:
                print(f"Time: {time.perf_counter() - start}")
                start = time.perf_counter()
                self.save_model(self.model)

    def save_model(self, model):
        model.save(str(TRAIN_DIRECTORY / "checkpoints" / datetime.datetime.now().strftime("%Y_%b_%d_%H_%M_%S_%f")))
        with open(TRAIN_DIRECTORY / "checkpoints" / "optimizer.json", mode="w", encoding="utf-8") as f:
            f.write(json.dumps(str(serialize(self.optimizer))))

        # Keep checkpoints to see elo rating later
        chkpts = os.listdir(TRAIN_DIRECTORY / "chkpts_to_elo")
        chkpts.sort()
        last_saved = datetime.datetime.strptime(chkpts[-1],"%Y_%b_%d_%H_%M_%S_%f")
        if (datetime.datetime.now() - last_saved).seconds > SAVE_FOR_ELO_AFTER_TIME:
            model.save(str(TRAIN_DIRECTORY / "chkpts_to_elo" / datetime.datetime.now().strftime("%Y_%b_%d_%H_%M_%S_%f")))

    def close(self, signal, frame):
        if self.data_loader_conn:
            self.data_loader_conn.close()
        if self.data_loader_process:
            self.data_loader_process.terminate()
        exit(0)

if __name__ == "__main__":
    print(f"Learner PID: {os.getpid()}")
    tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], enable=True)
    if check_enough_games():
        learner = Learner()

        signal(SIGINT, learner.close)
        signal(SIGTERM, learner.close)

        learner.start()
        learner.close(0,0)
    else:
        print(f"Not enough games in Experience Store. Minimum {MIN_STORED_GAMES} games are required.")