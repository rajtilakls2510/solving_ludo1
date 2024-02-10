import ludoc
import mcts
import time
import threading
import psutil
import tensorflow as tf

tf.config.experimental.set_memory_growth(tf.config.list_physical_devices("GPU")[0], True)

BATCH_SIZE = 512


@tf.function
def eval(network, inputs):
    return network(inputs, training=False)[:, 0]


def evaluator(eq, player):
    # This function is run on a different thread which continuously evaluates states in the queue

    while not eq.stop:
        states, indices = eq.get_elems_pending(n_elems=BATCH_SIZE)
        results = []
        if len(indices) > 0:
            results = eval(networks[player], tf.convert_to_tensor(states))
        #    results = [1.0] * len(indices)
        eq.set_elems_result(results, indices)


if __name__ == "__main__":
    # Initializing Game
    config = ludoc.GameConfig([["red", "yellow"], ["green", "blue"]])
    game_engine = ludoc.Ludo(config)
    state = game_engine.state.get()

    network = tf.keras.models.load_model("2023_Nov_10_04_08_24_131652")
    networks = [network for _ in range(state["n_players"])]

    # Initialize MCTS trees for each player
    trees = [mcts.MCTree(game_engine.state, i) for i in range(state["n_players"])]
    for tree in trees:
        tree.expand_root(game_engine.model)

    # Take Move

    state = game_engine.state.get()
    print(state)  # ,"\n", game_engine.state.get_tensor_repr(game_engine.model.config))
    while not state["game_over"]:
        player = state["current_player"]
        print("For Player:", player)
        for tree in trees:
            tree.prune_root(state["dice_roll"])
        # Initializing Evaluation Resources
        eq = mcts.EvaluationQueue(length=100_000, config=game_engine.model.config)
        t1 = threading.Thread(target=evaluator, args=(eq, player))
        t1.start()

        start = time.perf_counter_ns()
        # Searching
        print("Max Depth:",
              trees[player].mcts(simulations=100, model=game_engine.model, c_puct=3.0, n_vl=3, eq=eq, max_depth=1000))
        end = time.perf_counter_ns()
        print("Time:", (end - start) / 1e6, "ms")

        # Releasing Evaluation Resources
        eq.set_stop()
        t1.join()
        del eq

        # Selecting and taking move
        move_for_tree, move_for_engine, probs_list = trees[player].select_next_move()
        print(move_for_engine, move_for_tree)
        print(probs_list)
        game_engine.turn(move_for_engine, state["last_move_id"] + 1)
        state = game_engine.state.get()
        print(state)  # , "\n", game_engine.state.get_tensor_repr(game_engine.model.config))
        for tree in trees:
            print(f"Taking move on tree: {tree.owner}")
            tree.take_move(move_for_tree, game_engine.model)
        print("memory after", psutil.Process().memory_info().rss / 1024 ** 2)




