import rpyc
from signal import signal, SIGINT, SIGTERM
import threading
import json
import base64
import tensorflow as tf
from tensorflow.keras import Model, Input, layers
from pathlib import Path
import os
import datetime
import shutil

""" This file contains stuff related to the train server which serves the actor """

server = None
TRAIN_SERVER_PORT = 18861
TRAIN_DIRECTORY = Path("runs") / "run1"
MAX_CHECKPOINTS = 2

""" Hierarchy of store 
- runs/
    - run<i>/
        - checkpoints/
        - experience_store/
        - logs/
"""



def handle_close(signalnum, frame):
    server.close()
    print("Train Server Stopped")


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

        # TOOD: Delete older game files
        with open(TRAIN_DIRECTORY / "experience_store" / (time.strftime("%Y_%b_%d_%H_%M_%S_%f")+".json"), "w", encoding="utf-8") as f:
            f.write(str(data_store))
        with open(TRAIN_DIRECTORY / "logs" / (time.strftime("%Y_%b_%d_%H_%M_%S_%f")+".json"), "w", encoding="utf-8") as f:
            f.write(str(log))


    @rpyc.exposed
    def get_nnet_list(self):
        """This method sends back a list of all checkpoints present along with the latest one
        Return:
            - checkpoints = {"latest": name, "others": [name, ...]}
        """

        checkpoints = os.listdir(TRAIN_DIRECTORY / "checkpoints")
        remove = checkpoints[:len(checkpoints)-MAX_CHECKPOINTS]
        available = checkpoints[len(checkpoints)-MAX_CHECKPOINTS]

        for ch in remove:
            shutil.rmtree(TRAIN_DIRECTORY / "checkpoints" / ch)

        return available

    @rpyc.exposed
    def get_nnet(self, ckpt_name):
        """This method sends back the nnet architecture and parameters of the required checkpoint"""
        path = TRAIN_DIRECTORY / "checkpoints" / ckpt_name
        model = tf.keras.models.load_model(path)
        config = model.get_config()
        params = model.get_weights()
        for i in range(len(params)):
            params[i] = base64.b64encode(
                tf.io.serialize_tensor(tf.convert_to_tensor(params[i])).numpy()).decode('ascii')
        return json.dumps({"config": config, "params": params})



def start_server():
    global server
    server = ThreadedServer(TrainingService, port=TRAIN_SERVER_PORT)
    server.start()


if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer

    inp = Input(shape=(5,))
    x = layers.Dense(10)(inp)
    model = Model(inputs=inp, outputs=x)

    model.save(str(TRAIN_DIRECTORY / "checkpoints" / "model1"))
    model.save(str(TRAIN_DIRECTORY / "checkpoints" / "model2"))
    model.save(str(TRAIN_DIRECTORY / "checkpoints" / "model3"))
    model.save(str(TRAIN_DIRECTORY / "checkpoints" / "model4"))

    signal(SIGINT, handle_close)
    signal(SIGTERM, handle_close)
    threading.Thread(target=start_server).start()
    print("Train Server Started")



