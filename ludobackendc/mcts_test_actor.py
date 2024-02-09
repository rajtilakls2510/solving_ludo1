import ludoc
import mcts
import time
import threading

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
        tree.expand_root()


    # Take Move

    state = game_engine.state.get()
    for tree in trees:
        tree.prune_root(state["dice_roll"])
    player = state["current_player"]

    # Initializing Evaluation Resources

    eq = mcts.EvaluationQueue(length=100_000)
    t1 = threading.Thread(target=evaluator, args=(eq, networks[player]))
    t1.start()

    # Searching and Selecting move
    trees[player].mcts(simulations=1000, model=game_engine.model, player=0, c_puct=3.0, n_vl=3, eq=eq, max_depth=1000)
    move_idx = trees[player].select_next_move()
    # TODO: Take next move
    trees[player].take_move(move_idx) # TODO: Figure this out

    # Releasing Evaluation Resources
    eq.set_stop()
    t1.join()
    del eq


