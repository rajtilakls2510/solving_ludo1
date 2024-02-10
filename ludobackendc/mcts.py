# cython: cdivision = True

import cython
from cython.parallel import prange
from cython.cimports import ludoc
from cython.cimports.libc.stdlib import free, malloc, calloc, rand, RAND_MAX
from cython.cimports.openmp import omp_lock_t, omp_init_lock, omp_set_lock, omp_unset_lock, omp_destroy_lock
from cython.cimports.libc.math import exp, pow, sqrt
from cython.cimports.cytime import sleep


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def create_mcts_node(state: ludoc.StateStruct, parent: cython.pointer(MCTSNode)) -> cython.pointer(MCTSNode):
    node: cython.pointer(MCTSNode) = cython.cast(cython.pointer(MCTSNode), calloc(1, cython.sizeof(MCTSNode)))
    node.state = state
    node.parent = parent
    node.roll_num_moves = cython.NULL
    node.all_moves = cython.NULL
    node.expanded = False
    node.children = cython.NULL
    node.move_start = 0
    node.move_end = 0
    node.p = cython.NULL
    node.n = cython.NULL
    node.w = cython.NULL
    node.q = cython.NULL
    omp_init_lock(cython.address(node.access_lock))
    return node


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def free_mcts_node(node: cython.pointer(MCTSNode)) -> cython.void:
    # This function frees the node along with it's subtree recursively. Be careful.
    if node != cython.NULL:
        ludoc.free_state(node.state)
        omp_destroy_lock(cython.address(node.access_lock))
        if node.expanded and not node.state.game_over:
            if node.children != cython.NULL:
                i: cython.Py_ssize_t
                for i in range(node.move_start, node.move_end):
                    free_mcts_node(node.children[i])
                    node.children[i] = cython.NULL
            total_moves: cython.short = 0
            i: cython.Py_ssize_t
            for i in range(19):
                total_moves += node.roll_num_moves[i]
            for i in range(total_moves):
                if node.all_moves[i].n_rolls > 0:
                    ludoc.free_move(node.all_moves[i])
            free(node.roll_num_moves)
            free(node.all_moves)
            free(node.children)
            free(node.p)
            free(node.n)
            free(node.w)
            free(node.q)
        free(node)


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def prune(node: cython.pointer(MCTSNode), start: cython.short, end: cython.short) -> cython.void:
    # ONLY CALL PRUNE ON AN EXPANDED NODE [start is included, end is excluded]
    i: cython.Py_ssize_t
    for i in range(node.move_start, start):
        free_mcts_node(node.children[i])
        node.children[i] = cython.NULL
    for i in range(end, node.move_end):
        free_mcts_node(node.children[i])
        node.children[i] = cython.NULL
    node.move_start = start
    node.move_end = end


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def expand_mcts_node(node: cython.pointer(MCTSNode),
                     stars: cython.pointer(cython.short),
                     final_pos: cython.pointer(cython.short),
                     colour_tracks: cython.pointer(cython.short),
                     player_colours: cython.pointer(cython.short)) -> cython.void:
    # Ignore if the node is expanded.
    if not node.expanded:
        if not node.state.game_over:

            # Finding all possible moves
            all_moves_return: ludoc.AllPossibleMovesReturn = ludoc.all_possible_moves1(node.state, stars, final_pos,
                                                                                       colour_tracks, player_colours)

            # Calculating total number of moves along with "no move" moves for each roll
            total_moves: cython.short = 0
            i: cython.Py_ssize_t
            for i in range(19):
                total_moves += all_moves_return.roll_num_moves[i]
                if all_moves_return.roll_num_moves[
                    i] == 0:  # Putting a "no move" on rolls with no move. Doesn't matter if its not a valid roll
                    total_moves += 1

            # Copying roll_num_moves in node algon with "no move"
            node.roll_num_moves = cython.cast(cython.pointer(cython.short), calloc(19, cython.sizeof(cython.short)))
            for i in range(19):
                node.roll_num_moves[i] = all_moves_return.roll_num_moves[i]
                if all_moves_return.roll_num_moves[
                    i] == 0:  # Putting a "no move" on rolls with no move. Doesn't matter if its not a valid roll
                    node.roll_num_moves[i] = 1

            # Copying the moves and creating the next child of the tree
            node.all_moves = cython.cast(cython.pointer(ludoc.MoveStruct),
                                         calloc(total_moves, cython.sizeof(ludoc.MoveStruct)))
            node.children = cython.cast(cython.pointer(cython.pointer(MCTSNode)),
                                        calloc(total_moves, cython.sizeof(cython.pointer(MCTSNode))))
            last: cython.short = 0
            for i in range(19):
                node.state.dice_roll = ludoc.roll_sum_to_mod(i)
                if all_moves_return.roll_num_moves[i] == 0:
                    # Skipping assignment to this move because this will serve as a no move MoveStruct
                    node.children[last] = create_mcts_node(
                        ludoc.generate_next_state1(node.state, node.all_moves[last], colour_tracks, stars, final_pos,
                                                   player_colours), node)
                    last += 1
                else:
                    j: cython.Py_ssize_t
                    for j in range(node.roll_num_moves[i]):
                        node.all_moves[last] = all_moves_return.roll_moves[i][j]
                        node.children[last] = create_mcts_node(
                            ludoc.generate_next_state1(node.state, node.all_moves[last], colour_tracks, stars,
                                                       final_pos, player_colours), node)
                        last += 1
            node.move_start = 0
            node.move_end = total_moves

            # Allocating statistics for node
            node.p = cython.cast(cython.pointer(cython.double), calloc(total_moves, cython.sizeof(cython.double)))
            for i in range(total_moves):
                node.p[i] = 1.0
            node.n = cython.cast(cython.pointer(cython.int), calloc(total_moves, cython.sizeof(cython.int)))
            node.w = cython.cast(cython.pointer(cython.double), calloc(total_moves, cython.sizeof(cython.double)))
            node.q = cython.cast(cython.pointer(cython.double), calloc(total_moves, cython.sizeof(cython.double)))

            # Deallocating all_moves_return except the individual moves themselves and roll_num_moves
            for i in range(19):
                free(all_moves_return.roll_moves[i])
            free(all_moves_return.roll_moves)
            free(all_moves_return.roll_num_moves)
        node.expanded = True


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def get_random_roll_sum() -> cython.short:
    p: cython.int = rand() % 16 + 1  # generate randomly out of 1 - 16
    i: cython.short
    for i in range(1, 7):
        if i == 6:
            j: cython.short
            for j in range(1, 7):
                if j == 6:
                    k: cython.short
                    for k in range(1, 6):
                        p -= 1
                        if p == 0:
                            return i + j + k
                p -= 1
                if p == 0:
                    return i + j
        p -= 1
        if p == 0:
            return i


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def selection(node: cython.pointer(MCTSNode), c_puct: cython.double, n_vl: cython.int,
              move_indices: cython.pointer(cython.int),
              move_last: cython.pointer(cython.int), skip_initial_node: cython.bint) -> cython.pointer(MCTSNode):
    # When we find a node which is not expanded. It may also happen that after this instruction, another thread starts expanding the node.
    # But we make sure to continue selection for this thread later.
    k: cython.int = 0
    while node.expanded and not node.state.game_over:
        ms: cython.short = 0
        me: cython.short = 0
        if skip_initial_node:
            ms = node.move_start
            me = node.move_end
            skip_initial_node = False
        else:
            # Getting a random roll
            r: cython.short = get_random_roll_sum()

            # Calculating the move start and move end
            i: cython.Py_ssize_t
            sum: cython.short = 0
            for i in range(19):
                if i == r:
                    ms = sum
                    me = ms + node.roll_num_moves[i]
                    break
                sum += node.roll_num_moves[i]

        # Calculating u = c_puct * node.p[ms:me] * sqrt(sum(node.n[ms:me])) / (1 + node.n[ms:me])
        u: cython.pointer(cython.double) = cython.cast(cython.pointer(cython.double),
                                                       calloc(me - ms, cython.sizeof(cython.double)))
        sum2: cython.int = 0
        for i in range(ms, me):
            sum2 += node.n[i]
        sqrt_sum: cython.double = sqrt(sum2)

        for i in range(me - ms):
            u[i] = c_puct * node.p[i + ms] * sqrt_sum / (1 + node.n[i + ms])
        mi: cython.int = ms
        max: cython.double = node.q[ms] + u[0]
        for i in range(me - ms):
            if max < (node.q[i + ms] + u[i]):
                max = node.q[i + ms] + u[i]
                mi = i + ms
        move_indices[move_last[0]] = mi
        move_last[0] += 1
        free(u)

        # Adding virtual losses to node
        omp_set_lock(cython.address(node.access_lock))
        node.n[mi] += n_vl
        node.w[mi] -= n_vl
        omp_unset_lock(cython.address(node.access_lock))

        node = node.children[mi]
        k += 1
    return node


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def expansion(node: cython.pointer(MCTSNode),
              c_puct: cython.double, n_vl: cython.int,
              move_indices: cython.pointer(cython.int),
              move_last: cython.pointer(cython.int),
              stars: cython.pointer(cython.short),
              final_pos: cython.pointer(cython.short),
              colour_tracks: cython.pointer(cython.short),
              player_colours: cython.pointer(cython.short)) -> cython.pointer(MCTSNode):
    omp_set_lock(cython.address(node.access_lock))

    # If the node has not been expanded by another thread, expand it
    if not node.expanded:
        expand_mcts_node(node, stars, final_pos, colour_tracks, player_colours)
        # LOCK IS NOT RELEASED UNTIL p FOR node IS CALCULATED. THIS IS TO MAKE SURE OTHER THREADS WAIT FOR EXPANSION COMPLETION
    else:
        # Else, release lock immediately and resume from selection phase
        omp_unset_lock(cython.address(node.access_lock))
        if not node.state.game_over:
            node = selection(node, c_puct, n_vl, move_indices, move_last, False)
            node = expansion(node, c_puct, n_vl, move_indices, move_last, stars, final_pos, colour_tracks,
                             player_colours)
    return node


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def mcts_job(j: cython.Py_ssize_t,
             root: cython.pointer(MCTSNode),
             player: cython.short, c_puct: cython.double,
             n_vl: cython.int, eq: EvaluationQueue,
             max_depth: cython.int,
             stars: cython.pointer(cython.short),
             final_pos: cython.pointer(cython.short),
             colour_tracks: cython.pointer(cython.short),
             player_colours: cython.pointer(cython.short)) -> cython.int:
    node: cython.pointer(MCTSNode) = root
    move_indices: cython.pointer(cython.int) = cython.cast(cython.pointer(cython.int),
                                                           calloc(max_depth, cython.sizeof(cython.int)))
    move_last: cython.int = 0

    # SELECTION
    node = selection(node, c_puct, n_vl, move_indices, cython.address(move_last), True)

    # EXPANSION
    node = expansion(node, c_puct, n_vl, move_indices, cython.address(move_last), stars, final_pos, colour_tracks,
                     player_colours)

    # EVALUATION
    v: cython.double = 0.0
    if not node.state.game_over:
        node.state.current_player = player
        future_id: cython.int = add_to_eq(eq.queue_struct, node.state, cython.address(eq.insertion_lock))
        if future_id == -1:
            with cython.gil:
                print("Evaluation Queue Size Exceeded")
        while eq.queue_struct.queue[future_id].pending:
            sleep(0.0001)
        v = eq.queue_struct.queue[future_id].result
        # results: cython.pointer(cython.double) = cython.cast(cython.pointer(cython.double),
        #                                                      calloc(node.move_end - node.move_start,
        #                                                             cython.sizeof(cython.double)))
        # future_ids: cython.pointer(cython.int) = cython.cast(cython.pointer(cython.int),
        #                                                      calloc(node.move_end - node.move_start,
        #                                                             cython.sizeof(cython.int)))
        # i: cython.Py_ssize_t
        # for i in range(node.move_end - node.move_start):
        #     next_state: ludoc.StateStruct = node.children[i].state
        #     next_state.current_player = player
        #     future_ids[i] = add_to_eq(eq.queue_struct, next_state, cython.address(eq.insertion_lock))
        #     if future_ids[i] == -1:
        #         with cython.gil:
        #             print("Evaluation Queue Size Exceeded")
        # for i in range(node.move_end - node.move_start):
        #     while eq.queue_struct.queue[future_ids[i]].pending:
        #         sleep(0.001)
        #     results[i] = eq.queue_struct.queue[future_ids[i]].result

        # node.p = softmax(results)
        # sum_exp: cython.double = 0.0
        # i: cython.Py_ssize_t
        # for i in range(node.move_end - node.move_start):
        #     result: cython.double = exp(results[i])
        #     node.p[i] = result
        #     sum_exp += result
        # for i in range(node.move_end - node.move_start):
        #     node.p[i] /= sum_exp

        # v = sum(node.p * results)
        # v = 0.0
        # for i in range(node.move_end - node.move_start):
        #     v += node.p[i] * results[i]
        # free(future_ids)
        # free(results)
    else:
        # Checking if player is winner.
        # Alternatively we can check whether this player has already finished his game. This only works if the game
        # is over after one player completes.
        v = -1.0
        if ludoc.check_completed1(node.state, player, final_pos):
            v = 1.0

    # BACKUP

    omp_unset_lock(cython.address(node.access_lock))
    node = node.parent
    depth: cython.int = move_last
    while move_last > 0:
        move_last -= 1
        player_multiplier: cython.int = -1
        if node.state.current_player == player:
            player_multiplier = 1
        omp_set_lock(cython.address(node.access_lock))
        node.n[move_indices[move_last]] += 1 - n_vl
        node.w[move_indices[move_last]] += (player_multiplier * v) + n_vl
        node.q[move_indices[move_last]] = node.w[move_indices[move_last]] / node.n[move_indices[move_last]]
        omp_unset_lock(cython.address(node.access_lock))
        node = node.parent

    free(move_indices)
    return depth


@cython.cclass
class MCTree:
    # This is the python object for accessing MCTS tree and it's functions
    root: cython.pointer(MCTSNode)
    owner = cython.declare(cython.short, visibility="public")

    def __init__(self, current_state: ludoc.State, owner: cython.short):
        # Creating unexpanded root node
        # If state is not copied, when current_state object is deallocated, its state_struct will also get deallocated. This does not require us to hold the reference to the current_state object
        self.root = create_mcts_node(ludoc.copy_state(current_state.state_struct), cython.NULL)
        self.owner = owner

    def expand_root(self, model: ludoc.LudoModel):
        expand_mcts_node(self.root, model.stars, model.final_pos, model.colour_tracks, model.config.player_colours)

    def prune_root(self, roll: list):
        print("Inside prune")
        # Prunes the tree.
        r: cython.short = sum(roll)
        ms: cython.short = 0
        me: cython.short = 0
        s1: cython.short = 0
        for i in range(19):
            if i == r:
                ms = s1
                me = ms + self.root.roll_num_moves[i]
                break
            s1 += self.root.roll_num_moves[i]
        print("Pruning:", self.root.move_start, self.root.move_end, ms, me)
        prune(self.root, ms, me)
        print("After pruning")

    def mcts(self, simulations: cython.int, model: ludoc.LudoModel, c_puct: cython.double,
             n_vl: cython.int, eq: EvaluationQueue,
             max_depth: cython.int):
        # Runs MCTS for simulations using prange
        i: cython.Py_ssize_t
        depths: cython.pointer(cython.int) = cython.cast(cython.pointer(cython.int),
                                                         calloc(simulations, cython.sizeof(cython.int)))
        for i in prange(simulations, nogil=True):
            depths[i] = mcts_job(i, self.root, self.owner, c_puct, n_vl, eq, max_depth, model.stars, model.final_pos,
                                 model.colour_tracks, model.config.player_colours)
        max_depth: cython.int = 0
        for i in range(simulations):
            if depths[i] > max_depth:
                max_depth = depths[i]
        free(depths)
        return max_depth

    def select_next_move(self):
        # Make sure you call it on an expanded node, otherwise suffer the consequences

        # pi(a|s) = N(s,a) / sum(N(s,.))
        num_available_moves: cython.int = self.root.move_end - self.root.move_start
        probs: cython.pointer(cython.double) = cython.cast(cython.pointer(cython.double),
                                                           calloc(num_available_moves, cython.sizeof(cython.double)))

        sum: cython.double = 0.0
        i: cython.Py_ssize_t
        for i in range(num_available_moves):
            sum += self.root.n[self.root.move_start + i]
        probs_list = []
        for i in range(num_available_moves):
            probs[i] = cython.cast(cython.double, self.root.n[self.root.move_start + i]) / sum
            probs_list.append([probs[i], self.root.n[self.root.move_start + i], self.root.w[self.root.move_start + i],
                               self.root.q[self.root.move_start + i]])

        # Sampling from pi(a|s)
        random: cython.double = cython.cast(cython.double, rand()) / cython.cast(cython.double, RAND_MAX);
        sum = 0.0
        selected_move_idx: cython.int = self.root.move_start
        for i in range(num_available_moves):
            sum += probs[i]
            if random < sum:
                selected_move_idx = i + self.root.move_start
                break

        free(probs)

        # Sending back the data in a format that the user understands
        selected_move: ludoc.MoveStruct = self.root.all_moves[selected_move_idx]
        move_for_game_engine = []
        if selected_move.n_rolls == 0:
            move_for_game_engine = [[]]
        else:
            mappings = {
                "pawn": ["", "R1", "R2", "R3", "R4", "G1", "G2", "G3", "G4", "Y1", "Y2", "Y3", "Y4", "B1", "B2", "B3",
                         "B4"],
                "pos": ["", "RB1", "RB2", "RB3", "RB4", "GB1", "GB2", "GB3", "GB4", "YB1", "YB2", "YB3", "YB4", "BB1",
                        "BB2", "BB3", "BB4"]
                       + [f"P{i + 1}" for i in range(52)]
                       + ["RH1", "RH2", "RH3", "RH4", "RH5", "RH6", "GH1", "GH2", "GH3", "GH4", "GH5", "GH6", "YH1",
                          "YH2",
                          "YH3", "YH4", "YH5", "YH6", "BH1", "BH2", "BH3", "BH4", "BH5", "BH6"]
            }
            for i in range(selected_move.n_rolls):
                if selected_move.pawns[i] > 16:
                    p = []
                    p1: cython.int = selected_move.pawns[i]
                    while p1 != 0:
                        p.append(mappings["pawn"][p1 % 17])
                        p1 //= 17
                else:
                    p = mappings["pawn"][selected_move.pawns[i]]
                move_for_game_engine.append(
                    [p, mappings["pos"][selected_move.current_positions[i]],
                     mappings["pos"][selected_move.destinations[i]]])
        return selected_move_idx, move_for_game_engine, probs_list

    def take_move(self, move_idx: cython.short, model: ludoc.LudoModel):
        # Takes the move, updates the tree and root.
        previous_root: cython.pointer(MCTSNode) = self.root
        self.root = previous_root.children[move_idx]
        previous_root.children[
            move_idx] = cython.NULL  # Dereferencing the selected child from the parent before it gets freed by the following free node function call
        free_mcts_node(previous_root)
        if not self.root.expanded:
            self.expand_root(model)

    def __dealloc__(self):
        free_mcts_node(self.root)


QN = cython.struct(data=ludoc.StateStruct, pending=cython.bint, result=cython.double)
EQ = cython.struct(queue=cython.pointer(QN), front=cython.int, rear=cython.int,
                   length=cython.int)  # Length is not the no. of elems


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def add_to_eq(queue: cython.pointer(EQ), data: ludoc.StateStruct,
              insertion_lock: cython.pointer(omp_lock_t)) -> cython.int:
    ret: cython.int
    # This lock doesn't bottleneck that much
    omp_set_lock(insertion_lock)
    if (queue.rear + 1) % queue.length == queue.front:
        ret = -1
    else:
        queue.queue[queue.rear] = QN(data=data, pending=True,
                                     result=0.0)  # Make sure "data" is not freed while in queue
        ret = queue.rear
        queue.rear = (queue.rear + 1) % queue.length
    omp_unset_lock(insertion_lock)
    return ret


@cython.cclass
class EvaluationQueue:
    queue_struct: cython.pointer(EQ)
    insertion_lock: omp_lock_t
    stop = cython.declare(cython.bint, visibility="public")
    config: ludoc.GameConfig

    def __init__(self, length: cython.int, config: ludoc.GameConfig):
        self.stop = False
        omp_init_lock(cython.address(self.insertion_lock))
        self.queue_struct = cython.cast(cython.pointer(EQ), calloc(1, cython.sizeof(EQ)))
        self.queue_struct.queue = cython.cast(cython.pointer(QN), calloc(length, cython.sizeof(QN)))
        i: cython.Py_ssize_t
        for i in range(length):
            self.queue_struct.queue[i].pending = False
        self.queue_struct.front = 0
        self.queue_struct.rear = 0
        self.queue_struct.length = length
        self.config = config

    def get_elems_pending(self, n_elems: cython.int):
        accumulated_data = []
        accumulated_indices = []
        accum: cython.int = 0
        # Collect max(n_elems, number of left) Elements
        i: cython.int = self.queue_struct.front
        while i != self.queue_struct.rear and accum < n_elems:
            if self.queue_struct.queue[i].pending:
                state: ludoc.State = ludoc.State()
                state.set_structure(ludoc.copy_state(self.queue_struct.queue[i].data))
                accumulated_data.append(state.get_tensor_repr(self.config))
                accumulated_indices.append(i)
                accum += 1
                del state
            i = (i + 1) % self.queue_struct.length
        if len(accumulated_indices) > 0:
            return accumulated_data, accumulated_indices
        return [], []

    def set_elems_result(self, results, results_indices: list):

        # Setting the results
        i: cython.int
        for i, res in zip(results_indices, results):
            self.queue_struct.queue[i].result = res
            self.queue_struct.queue[i].pending = False
        # Incrementing front so that queue is freed up
        while self.queue_struct.front != self.queue_struct.rear and not self.queue_struct.queue[
            self.queue_struct.front].pending:
            self.queue_struct.front = (self.queue_struct.front + 1) % self.queue_struct.length

        #print(self.queue_struct.front, self.queue_struct.rear)

    def set_stop(self):
        self.stop = True

    def __dealloc__(self):
        omp_destroy_lock(cython.address(self.insertion_lock))
        free(self.queue_struct.queue)
        free(self.queue_struct)
