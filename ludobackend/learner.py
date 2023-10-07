import json
import random
import gc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
from signal import signal, SIGINT, SIGTERM
import datetime
import tensorflow as tf
import numpy as np

from queue import Queue
tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], enable=True)

""" This file contains only stuff related to the learner """

DIRECTORY = Path("runs")
TRAIN_DIRECTORY = DIRECTORY / "run1"
MIN_STORED_GAMES = 1
BATCH_SIZE = 512
NUM_FILES_TO_FETCH_BATCH = 2
MIN_NUM_JOBS = 4
NUM_BATCHES = 50_000
SAVE_EVERY_BATCHES = 10_000


def check_enough_games():
    files = os.listdir(TRAIN_DIRECTORY / "experience_store")
    return len(files) >= MIN_STORED_GAMES


class DataLoader:

    def __init__(self, min_num_jobs_in_queue=4):
        self.executor = ThreadPoolExecutor(max_workers=MIN_NUM_JOBS)
        self.prefetch_queue = Queue()
        self.num_jobs = min_num_jobs_in_queue
        self.experience_store_path = TRAIN_DIRECTORY / "experience_store"
        for _ in range(self.num_jobs):
            self.executor.submit(self.fetch)

    def get_pawn_permutation(self):
        perm = np.zeros(shape=(4, 4))
        permuted_indices = np.random.permutation(4)
        for i in range(4):
            perm[i, permuted_indices[i]] = 1
        return perm

    def fetch(self):
        states = []
        rewards = []
        for _ in range(NUM_FILES_TO_FETCH_BATCH):
            file = random.choice(os.listdir(self.experience_store_path))
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

                # Applying pawn augmentation
                permutation_array = np.eye(N=21)
                permutation_array[:4, :4] = self.get_pawn_permutation() # Red
                permutation_array[4:8, 4:8] = self.get_pawn_permutation() # Green
                permutation_array[8:12, 8:12] = self.get_pawn_permutation() # Yellow
                permutation_array[12:16, 12:16] = self.get_pawn_permutation() # Blue
                state = state @ permutation_array

                # Applying turn augmentation
                player = random.choice(np.arange(4)+1)
                state[:, -1] = player

                reward = [1] if state[0, -1] == winner_player else [-1]

                states.append(state)
                rewards.append(reward)
        self.prefetch_queue.put((tf.convert_to_tensor(states, dtype=tf.float32), tf.convert_to_tensor(rewards, dtype=tf.float32)))
        del game_data
        gc.collect()

    def get_batch(self):
        for _ in range(self.num_jobs - self.prefetch_queue.qsize()):
            self.executor.submit(self.fetch)
        return self.prefetch_queue.get()

    def close(self):
        self.executor.shutdown(wait=True)


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
        self.data_loader = DataLoader(min_num_jobs_in_queue=MIN_NUM_JOBS)
        self.load_latest_checkpoint()
        self.loss = tf.keras.losses.MeanSquaredError()
        self.optimizer = tf.keras.optimizers.Adam(learning_rate=0.001) # TODO: Figure out a learning rate schedule
        self.data_loader.fetch()
        for i in range(NUM_BATCHES):
            print(f"Batch: {i}. QSize: {self.data_loader.prefetch_queue.qsize()}")
            x_batch, y_batch = self.data_loader.get_batch()
            l = self.train_step(x_batch, y_batch)
            # TODO: Log loss for training
            if (i+1) % SAVE_EVERY_BATCHES == 0:
                self.save_model(self.model)

    def save_model(self, model):
        model.save(str(TRAIN_DIRECTORY / "checkpoints" / datetime.datetime.now().strftime("%Y_%b_%d_%H_%M_%S_%f")))

    def close(self, signal, frame):
        if self.model:
            self.save_model(self.model)
        self.data_loader.close()

if __name__ == "__main__":
    if check_enough_games():
        learner = Learner()

        signal(SIGINT, learner.close)
        signal(SIGTERM, learner.close)

        learner.start()
        learner.close(0,0)
    else:
        print(f"Not enough games in Experience Store. Minimum {MIN_STORED_GAMES} games are required.")