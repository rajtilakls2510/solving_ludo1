import rpyc
from signal import signal, SIGINT, SIGTERM
import threading

""" This file contains stuff related to the train server which serves the actor """

server = None
TRAIN_SERVER_PORT = 18861


def handle_close(signalnum, frame):
    server.close()
    print("RPyC Server Stopped")


@rpyc.service
class TrainingService(rpyc.Service):

    def on_connect(self, conn):
        print("Actor Connected")

    def on_disconnect(self, conn):
        print("Actor Disconnected")

    @rpyc.exposed
    def push_game_data(self, data):
        """This method is used to push its recent game data which consists of logging data and
        game states for experience store """
        pass

    @rpyc.exposed
    def get_nnet_list(self):
        """This method sends back a list of all checkpoints present along with the latest one"""
        pass

    @rpyc.exposed
    def get_nnet(self, ckpt_name):
        """This method sends back the nnet architecture and parameters of the required checkpoint"""
        pass


def start_server():
    global server
    server = ThreadedServer(TrainingService, port=TRAIN_SERVER_PORT)
    server.start()


if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer

    signal(SIGINT, handle_close)
    signal(SIGTERM, handle_close)
    threading.Thread(target=start_server).start()
    print("Train Server Started")



