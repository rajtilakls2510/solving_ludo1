import rpyc

""" This file only contains stuff related to actor and MCTS search """


TRAIN_SERVER_IP = "localhost"
TRAIN_SERVER_PORT = 18861
NUM_GAMES = 10

train_server_conn = None


def start():
    game = 0
    while game < NUM_GAMES:
        # TODO: Initialize game config and game engine
        # TODO: Pull Network architectures and parameters from train_server
        # TODO: Initialize Logging and other data stores that are going to be needed during game play
        # TODO: Start generating game
        # TODO: Send accumulated log data and other data to train_server

        game += 1


if __name__ == "__main__":
    """ Initialize some parameters and start generating games after contacting the training server """
    try:
        train_server_conn = rpyc.connect(TRAIN_SERVER_IP, TRAIN_SERVER_PORT)
        start()
    except:
        print("Couldn't connect to the Train Server")
