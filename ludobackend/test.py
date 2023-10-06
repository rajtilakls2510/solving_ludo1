import base64
from evaluator import EvaluatorMain
import multiprocessing
import rpyc
from ludo import Ludo, LudoModel, GameConfig
import json
import time
import tensorflow as tf
from concurrent.futures import ThreadPoolExecutor

TRAIN_SERVER_IP = "localhost"
TRAIN_SERVER_PORT = 18861
EVALUATOR_PORT = 18862
EVALUATION_BATCH_SIZE = 4096

def send_for_eval(j):
    start = time.perf_counter()
    serialized_tensor = base64.b64encode(
        tf.io.serialize_tensor(tf.zeros(shape=(512, 59, 42))).numpy()).decode('ascii')
    results = eval_server_conn.root.evaluate(game_config.players[ j%2 ].name, serialized_tensor)
    results = tf.io.parse_tensor(base64.b64decode(results), out_type=tf.float32)
    print(f"J={j}, Eval time: {time.perf_counter() - start}")

if __name__=="__main__":

    evaluator_process = multiprocessing.Process(target=EvaluatorMain.process_starter, args=(TRAIN_SERVER_IP, TRAIN_SERVER_PORT, EVALUATOR_PORT, EVALUATION_BATCH_SIZE), name="Evaluator")
    evaluator_process.start()

    # time.sleep(1)
    eval_server_conn = rpyc.connect("localhost", EVALUATOR_PORT)

    for i in range(10):
        game_config = GameConfig([[LudoModel.RED, LudoModel.YELLOW], [LudoModel.GREEN,LudoModel.BLUE]])
        game_engine = Ludo(game_config)

        eval_server_conn.root.on_game_start(json.dumps(game_config.get_dict()))

        with ThreadPoolExecutor(max_workers=14) as executor:
            for j in range(500):
                executor.submit(send_for_eval, j)

        eval_server_conn.root.on_game_end()
        print(f"Game: {i}")

    evaluator_process.terminate()