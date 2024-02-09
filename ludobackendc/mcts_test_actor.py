import ludoc
import mcts
import time
import threading
import psutil

BATCH_SIZE = 1024


def evaluator(eq, networks=None):
    # This function is run on a different thread which continuously evaluates states in the queue
    while not eq.stop:
        states_dict = eq.get_elems_pending(n_elems=BATCH_SIZE)
        # TODO: Stack the states
        # TODO: Get results of the network
        results = {k: 1.0 for k in states_dict}
        eq.set_elems_result(results)
        time.sleep(0.0001)


if __name__ == "__main__":
    # Initializing Game
    config = ludoc.GameConfig([["red", "yellow"], ["green", "blue"]])
    game_engine = ludoc.Ludo(config)
    state = game_engine.state.get()

    # TODO: Pull Networks
    networks = [0 for _ in range(state["n_players"])]

    # Initialize MCTS trees for each player
    trees = [mcts.MCTree(game_engine.state, i) for i in range(state["n_players"])]
    for tree in trees:
        tree.expand_root(game_engine.model)

    # Take Move

    state = game_engine.state.get()
    print(state)
    for _ in range(6):
        player = state["current_player"]
        print("For Player:", player)
        for tree in trees:
            tree.prune_root(state["dice_roll"])
        # Initializing Evaluation Resources
        eq = mcts.EvaluationQueue(length=100_000)
        t1 = threading.Thread(target=evaluator, args=(eq, networks[player]))
        t1.start()

        start = time.perf_counter_ns()
        # Searching
        print("Max Depth:",
              trees[player].mcts(simulations=1_000, model=game_engine.model, c_puct=3.0, n_vl=3, eq=eq, max_depth=1000))
        end = time.perf_counter_ns()
        print("Time:", (end - start) / 1e6, "ms")

        # Releasing Evaluation Resources
        eq.set_stop()
        t1.join()
        del eq

        # Selecting and taking move
        move_for_tree, move_for_engine = trees[player].select_next_move()
        print(move_for_engine, move_for_tree)
        game_engine.turn(move_for_engine, state["last_move_id"] + 1)
        state = game_engine.state.get()
        print(state, "memory", psutil.Process().memory_info().rss / 1024 ** 2)
        for tree in trees:
            tree.take_move(move_for_tree, game_engine.model)
        print("memory after", psutil.Process().memory_info().rss / 1024 ** 2)




