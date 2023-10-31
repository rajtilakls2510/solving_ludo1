import rpyc
from signal import signal, SIGINT, SIGTERM
import threading
import json
import os
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
import base64
import tensorflow as tf
# tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], True)
from pathlib import Path
import time
import argparse
import datetime
import shutil
# from model import nn_model

""" This file contains stuff related to the train server which serves the actor """

server = None
TRAIN_SERVER_PORT = 18861   # The port at which the train server is expected to run at
DIRECTORY = Path("runs")
TRAIN_DIRECTORY = DIRECTORY / "run2"
MAX_CHECKPOINTS = 200     # Maximum number of checkpoints that should be stored
MAX_EXP_STORE_GAMES = 500     # Maximum number of games to store in experience store
MAX_LOG_GAMES = 100

""" Hierarchy of store 
- runs/
    - run<i>/
        - checkpoints/
        - experience_store/
        - logs/
        - chkpts_to_elo/
"""



def handle_close(signalnum, frame):
    server.close()
    print("Train Server Stopped")
    exit(0)


@rpyc.service
class TrainingService(rpyc.Service):

    def on_connect(self, conn):
        print("Actor Connected")

    def on_disconnect(self, conn):
        print("Actor Disconnected")

    @rpyc.exposed
    def push_game_data(self, data_store, log):
        """This method is used to push its recent game data which consists of logging data and
        game states for experience store """
        os.makedirs(TRAIN_DIRECTORY / "experience_store", exist_ok=True)
        os.makedirs(TRAIN_DIRECTORY / "logs", exist_ok=True)
        time = datetime.datetime.now()

        # Storing game data in Experience Store
        with open(TRAIN_DIRECTORY / "experience_store" / (time.strftime("%Y_%b_%d_%H_%M_%S_%f")+".json"), "w", encoding="utf-8") as f:
            f.write(str(data_store))

        # Deleting older game files
        games = os.listdir(TRAIN_DIRECTORY / "experience_store")
        if len(games) > MAX_EXP_STORE_GAMES:
            games.sort()
            remove = games[:len(games) - MAX_EXP_STORE_GAMES]

            for gm in remove:
                try:
                    os.remove(TRAIN_DIRECTORY / "experience_store" / gm)
                except:
                    pass

        # Storing logs
        with open(TRAIN_DIRECTORY / "logs" / (time.strftime("%Y_%b_%d_%H_%M_%S_%f")+".json"), "w", encoding="utf-8") as f:
            f.write(str(log))

        # Deleting older log files
        games = os.listdir(TRAIN_DIRECTORY / "logs")
        if len(games) > MAX_LOG_GAMES:
            games.sort()
            remove = games[:len(games) - MAX_LOG_GAMES]
            for gm in remove:
                try:
                    os.remove(TRAIN_DIRECTORY / "logs" / gm)
                except:
                    pass


    @rpyc.exposed
    def get_nnet_list(self):
        """This method sends back a list of all checkpoints in ascending order of its timestamp. The last one is always the latest checkpoint.
        """

        checkpoints = [dir for dir in os.listdir(TRAIN_DIRECTORY / "checkpoints") if len(dir.split(".")) == 1]
        checkpoints.sort()
        available = checkpoints
        if len(checkpoints) > MAX_CHECKPOINTS:
            remove = checkpoints[:len(checkpoints)-MAX_CHECKPOINTS]
            available = checkpoints[len(checkpoints)-MAX_CHECKPOINTS:]

            for ch in remove:
                try:
                    shutil.rmtree(TRAIN_DIRECTORY / "checkpoints" / ch)
                except:
                    pass

        return available

    @rpyc.exposed
    def get_nnet(self, ckpt_name):
        """This method sends back the nnet architecture and parameters of the required checkpoint"""
        path = TRAIN_DIRECTORY / "checkpoints" / ckpt_name
        try:
            model = tf.keras.models.load_model(path)
        except:
            # If the latest checkpoint is still being saved, an error is thrown. Handling that error by loading the second last checkpoint
            checkpoints = [dir for dir in os.listdir(TRAIN_DIRECTORY / "checkpoints") if len(dir.split(".")) == 1]
            checkpoints.sort()
            path = TRAIN_DIRECTORY / "checkpoints" / checkpoints[-2]
            model = tf.keras.models.load_model(path)
        config = model.get_config()
        params = model.get_weights()
        for i in range(len(params)):
            params[i] = base64.b64encode(
                tf.io.serialize_tensor(tf.convert_to_tensor(params[i])).numpy()).decode('ascii')
        return json.dumps({"config": config, "params": params})

    @rpyc.exposed
    def get_log_filenames(self, last_amount):
        runs = os.listdir(DIRECTORY)
        out = []
        for r in runs:
            l = os.listdir(DIRECTORY / r / "logs")
            l.sort()
            if len(l) > last_amount:
                l = l[len(l) - last_amount:]
            l.reverse()
            out.append({"run": r, "files": l})
        return json.dumps(out)

    @rpyc.exposed
    def get_log_file(self, path_list):
        path = DIRECTORY
        for p in path_list:
            path = path / p

        with open(path, mode="r", encoding="utf-8") as f:
            s = f.read()
        return s

def start_server():
    global server
    server = ThreadedServer(TrainingService, port=TRAIN_SERVER_PORT)
    server.start()


if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer
    print(f"Train Server PID: {os.getpid()}")
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18861,
                        help="The port at which this train server will run")
    args = parser.parse_args()
    TRAIN_SERVER_PORT = args.port
    signal(SIGINT, handle_close)
    signal(SIGTERM, handle_close)
    threading.Thread(target=start_server).start()
    print("Train Server Started")

    # You have to keep the main process alive to catch signals
    while True:
        time.sleep(1)



