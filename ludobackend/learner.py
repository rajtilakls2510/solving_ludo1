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

tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], enable=True)

""" This file contains only stuff related to the learner """

DIRECTORY = Path("runs")
TRAIN_DIRECTORY = DIRECTORY / "run1"
MIN_STORED_GAMES = 1
BATCH_SIZE = 512
NUM_FILES_TO_FETCH_BATCH = 8
MIN_NUM_JOBS = 14
NUM_BATCHES = 50_000
SAVE_EVERY_BATCHES = 100
PREFETCHER_PORT = 18863



# ========================== Pre-fetcher Process =======================================

@rpyc.service
class DataLoaderService(rpyc.Service):

    @rpyc.exposed
    def get_batch(self):
        states, rewards = DataLoader.data_loader_object.get_batch()
        states = base64.b64encode(
            tf.io.serialize_tensor(states).numpy()).decode('ascii')
        rewards = base64.b64encode(
            tf.io.serialize_tensor(rewards).numpy()).decode('ascii')
        return json.dumps([states, rewards])

    @rpyc.exposed
    def get_qsize(self):
        return DataLoader.data_loader_object.prefetch_queue.qsize()


class DataLoader:
    data_loader_object = None

    def __init__(self, min_num_jobs_in_queue=4, server=None):
        self.server = server
        self.executor = ThreadPoolExecutor(max_workers=min_num_jobs_in_queue)
        self.prefetch_queue = Queue()
        self.num_jobs = min_num_jobs_in_queue
        self.experience_store_path = TRAIN_DIRECTORY / "experience_store"
        for _ in range(self.num_jobs):
            self.executor.submit(self.fetch)

    @classmethod
    def process_starter(cls, prefetcher_port, min_num_jobs_in_queue):
        print(f"Pre-fetcher Process started PID: {os.getpid()}")

        signal(SIGINT, DataLoader.process_terminator)
        signal(SIGTERM, DataLoader.process_terminator)
        server = ThreadedServer(DataLoaderService, port=prefetcher_port)
        t1 = threading.Thread(target=server.start)
        t1.start()

        DataLoader.data_loader_object = DataLoader(min_num_jobs_in_queue, server)

        # Keeping the process alive
        event = threading.Event()
        event.wait()

    @classmethod
    def process_terminator(cls, signum, frame):
        if DataLoader.data_loader_object:
            DataLoader.data_loader_object.close()
        exit(0)

    def get_pawn_permutation(self):
        perm = np.zeros(shape=(4, 4))
        permuted_indices = np.random.permutation(4)
        for i in range(4):
            perm[i, permuted_indices[i]] = 1
        return perm

    def fetch(self):
        states = []
        rewards = []
        files = random.choices(os.listdir(self.experience_store_path), k=NUM_FILES_TO_FETCH_BATCH)
        for file in files:
            try:
                with open(self.experience_store_path / file, mode="r", encoding="utf-8") as f:
                    game_data = json.loads(f.read())
            except:
                # To maintain max store constraint if the train server has removed the file, read another file
                file = random.choice(os.listdir(self.experience_store_path))
                with open(self.experience_store_path / file, mode="r", encoding="utf-8") as f:
                    game_data = json.loads(f.read())

            winner_player = game_data["player_won"]
            num_states = len(game_data["states"])
            for _ in range(BATCH_SIZE // NUM_FILES_TO_FETCH_BATCH):
                chosen_state = np.random.randint(low=0, high=num_states)
                state = np.array(game_data["states"][chosen_state])

                # Applying turn augmentation
                player = random.choice(np.arange(4) + 1)
                state[:, -1] = player

                # Applying pawn augmentation
                permutation_array = np.eye(N=21)
                permutation_array[:4, :4] = self.get_pawn_permutation()  # Red
                permutation_array[4:8, 4:8] = self.get_pawn_permutation()  # Green
                permutation_array[8:12, 8:12] = self.get_pawn_permutation()  # Yellow
                permutation_array[12:16, 12:16] = self.get_pawn_permutation()  # Blue
                state = state @ permutation_array

                reward = [1] if state[0, -1] == winner_player else [-1]

                states.append(state)
                rewards.append(reward)
        self.prefetch_queue.put((tf.convert_to_tensor(states, dtype=tf.float32), tf.convert_to_tensor(rewards, dtype=tf.float32)))

    def get_batch(self):
        for _ in range(min(4, self.num_jobs - self.prefetch_queue.qsize())):
            self.executor.submit(self.fetch)
        return self.prefetch_queue.get()

    def close(self):
        if self.server:
            self.server.close()
        self.executor.shutdown(wait=True)


# ========================== Learner Main Process =======================================


def check_enough_games():
    files = os.listdir(TRAIN_DIRECTORY / "experience_store")
    return len(files) >= MIN_STORED_GAMES


class Learner:

    def load_latest_checkpoint(self):
        CHKPT_DIRECTORY = TRAIN_DIRECTORY / "checkpoints"
        chkpt_names = os.listdir(CHKPT_DIRECTORY)
        chkpt_names.sort()
        latest_model = chkpt_names[-1]
        path = CHKPT_DIRECTORY / latest_model
        self.model = tf.keras.models.load_model(path)
        print(f"Loaded model {path}")

    @tf.function
    def train_step(self, x_batch, y_batch):
        with tf.GradientTape() as tape:
            y_pred = self.model(x_batch)
            l = self.loss(y_batch, y_pred)

        grads = tape.gradient(l, self.model.trainable_variables)
        self.optimizer.apply_gradients(zip(grads, self.model.trainable_variables))
        return l

    def start(self):

        # Creating a background process for Data Loading
        self.data_loader_process = multiprocessing.Process(target=DataLoader.process_starter, args=(PREFETCHER_PORT, MIN_NUM_JOBS))
        self.data_loader_process.start()
        self.data_loader_conn = rpyc.connect("localhost", PREFETCHER_PORT)

        self.load_latest_checkpoint()
        self.loss = tf.keras.losses.MeanSquaredError()
        self.optimizer = tf.keras.optimizers.Adam(learning_rate=0.001) # TODO: Figure out a learning rate schedule
        start = time.perf_counter()
        for i in range(NUM_BATCHES):
            print(f"Batch: {i}. QSize: {self.data_loader_conn.root.get_qsize()}")
            x_batch, y_batch = json.loads(self.data_loader_conn.root.get_batch())
            x_batch = tf.io.parse_tensor(base64.b64decode(x_batch), out_type=tf.float32)
            y_batch = tf.io.parse_tensor(base64.b64decode(y_batch), out_type=tf.float32)
            # x_batch, y_batch = self.data_loader_conn.root.get_batch()
            l = self.train_step(x_batch, y_batch)
            # TODO: Log loss for training
            if (i+1) % SAVE_EVERY_BATCHES == 0:
                print(f"Time: {time.perf_counter() - start}")
                start = time.perf_counter()
                self.save_model(self.model)

    def save_model(self, model):
        model.save(str(TRAIN_DIRECTORY / "checkpoints" / datetime.datetime.now().strftime("%Y_%b_%d_%H_%M_%S_%f")))

    def close(self, signal, frame):
        if self.model:
            self.save_model(self.model)
        self.data_loader_conn.close()
        if self.data_loader_process:
            self.data_loader_process.terminate()

if __name__ == "__main__":
    if check_enough_games():
        learner = Learner()

        signal(SIGINT, learner.close)
        signal(SIGTERM, learner.close)

        learner.start()
        learner.close(0,0)
    else:
        print(f"Not enough games in Experience Store. Minimum {MIN_STORED_GAMES} games are required.")