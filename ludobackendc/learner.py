import json
import os
import argparse
import datetime
from pathlib import Path
import numpy as np
import random
import cysimdjson
import tensorflow as tf

tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], enable=True)


def check_enough_games(min_games, store_path):
    return len(os.listdir(store_path)) >= min_games


class SaveCallback(tf.keras.callbacks.Callback):

    def __init__(self, config_file):
        super().__init__()
        self.config_file = config_file

    def on_epoch_end(self, epoch, logs=None):
        with open(self.config_file, "r", encoding="utf-8") as f:
            config = json.loads(f.read())
        current_checkpoint = datetime.datetime.now().strftime('%Y_%b_%d_%H_%M_%S_%f')
        self.root_path = Path(config["root_path"])
        self.checkpoints_subpath = self.root_path / config["checkpoints_subpath"]
        self.model.save(
            str(self.checkpoints_subpath / current_checkpoint))
        config["evaluator"]["newest_checkpoint"] = current_checkpoint
        config["evaluator"]["evaluated"] = False
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(config))


class Learner:

    def __init__(self, config_file):
        self.config_file = config_file
        self.network = None

    def load_hyper_parameters(self):
        with open(self.config_file, "r", encoding="utf-8") as f:
            config = json.loads(f.read())
        self.root_path = Path(config["root_path"])
        self.store_path = self.root_path / config["experience_store_subpath"]
        self.checkpoints_subpath = self.root_path / config["checkpoints_subpath"]
        self.batch_size = config["learner"]["batch_size"]
        self.initial_batch = config["learner"]["initial_batch"]
        self.final_batch = config["learner"]["final_batch"]
        self.save_every_batches = config["learner"]["save_every_batches"]
        self.path_newest_checkpoint = self.checkpoints_subpath / config["evaluator"]["newest_checkpoint"]
        self.lr_boundaries = config["learner"]["lr_schedule"]["boundaries"]
        self.lr_lrs = config["learner"]["lr_schedule"]["lrs"]
        if self.network:
            self.network.optimizer.learning_rate = tf.keras.optimizers.schedules.PiecewiseConstantDecay(
                boundaries=self.lr_boundaries,
                values=self.lr_lrs)

    def get_pawn_permutation(self):
        # This function returns the permutation matrix for one colour of pawns
        perm = np.zeros(shape=(4, 4))
        permuted_indices = np.random.permutation(4)
        for i in range(4):
            perm[i, permuted_indices[i]] = 1
        return perm

    def get_elements(self):
        parser = cysimdjson.JSONParser()
        while True:
            file = random.choices(os.listdir(self.store_path), k=1)[0]
            game_data = parser.load(str(self.store_path / file))
            winner_player = game_data["player_won"]
            num_states = len(game_data["states"])
            # Choose one state
            chosen_state = np.random.randint(low=0, high=num_states)
            # Parse a state
            state = np.zeros(shape=(59, 25))
            for i in range(59):
                for j in range(25):
                    state[i, j] = game_data["states"][chosen_state][i][j]
            # Apply turn augmentation
            player = random.choice(np.unique(state[0, 16:20]))
            state[:, 20] = player

            # Apply pawn augmentation
            permutation_array = np.eye(N=25)
            permutation_array[:4, :4] = self.get_pawn_permutation()  # Red
            permutation_array[4:8, 4:8] = self.get_pawn_permutation()  # Green
            permutation_array[8:12, 8:12] = self.get_pawn_permutation()  # Yellow
            permutation_array[12:16, 12:16] = self.get_pawn_permutation()  # Blue
            state = state @ permutation_array

            # Select the appropriate reward based on who won
            reward = [1] if state[0, -1] == winner_player else [-1]
            yield tf.convert_to_tensor(state, dtype=tf.float32), tf.convert_to_tensor(reward, dtype=tf.float32)

    def train(self):
        self.load_hyper_parameters()
        self.network = tf.keras.models.load_model(self.path_newest_checkpoint)
        self.network.optimizer.learning_rate = tf.keras.optimizers.schedules.PiecewiseConstantDecay(
            boundaries=self.lr_boundaries,
            values=self.lr_lrs)
        self.network.optimizer.iterations = tf.Variable(self.initial_batch, dtype=tf.float32)
        print(self.network.optimizer.iterations)
        print(f"Loaded Network: {self.path_newest_checkpoint}")
        save_callback = SaveCallback(self.config_file)

        dataset = tf.data.Dataset \
            .from_generator(self.get_elements, output_signature=(
        tf.TensorSpec(shape=(59, 25), dtype=tf.float32), tf.TensorSpec(shape=(1,), dtype=tf.float32))) \
            .batch(self.batch_size) \
            .prefetch(tf.data.AUTOTUNE)
        #
        # @tf.function
        # def get_dataset():
        #     return tf.data.Dataset.from_generator(self.get_elements, output_signature=(
        #         tf.TensorSpec(shape=(59, 25), dtype=tf.float32), tf.TensorSpec(shape=(1,), dtype=tf.float32)))
        #
        # dataset = tf.data.Dataset.range(2).interleave(lambda _: get_dataset(),
        #                                               num_parallel_calls=tf.data.AUTOTUNE).batch(
        #     self.batch_size).prefetch(tf.data.AUTOTUNE)
        batch = self.initial_batch
        while batch < self.final_batch:
            history = self.network.fit(dataset, epochs=1, steps_per_epoch=self.save_every_batches,
                                       callbacks=[save_callback])
            batch += self.save_every_batches

        print("Training Complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path", type=str, default="train_config.json",
                        help="The config file that defines the configuration of the training run")
    args = parser.parse_args()
    config_file = args.config_path

    l = Learner(config_file)

    with open(config_file, "r", encoding="utf-8") as f:
        config = json.loads(f.read())
    root_path = Path(config["root_path"])
    if check_enough_games(config["learner"]["min_stored_games"], root_path / config["experience_store_subpath"]):
        l.train()
