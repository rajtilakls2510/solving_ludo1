# cython: cdivision = True

import cython
from cython.parallel import prange
from cython.cimports import ludoc
from cython.cimports.libc.stdlib import free, malloc, calloc, rand
from cython.cimports.openmp import omp_lock_t, omp_init_lock, omp_set_lock, omp_unset_lock, omp_destroy_lock
from cython.cimports.libc.math import exp, pow, sqrt
from cython.cimports.cytime import sleep


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def create_mcts_node(state: ludoc.StateStruct, parent: cython.pointer(MCTSNode)) -> cython.pointer(MCTSNode):
    node: cython.pointer(MCTSNode) = cython.cast(cython.pointer(MCTSNode), calloc(0, cython.sizeof(MCTSNode)))
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
        if node.expanded:
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
def expand_mcts_node(node: cython.pointer(MCTSNode)) -> cython.void:
    # TODO: Expand MCTS Node
    pass


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def get_random_roll_sum() -> cython.short:
    p: cython.int = rand() % 16 + 1  # generate randomly out of 1 - 16
    r: cython.short = 0
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
                            r = i + j + k
                            break
                p -= 1
                if p == 0:
                    r = i + j
                    break
        p -= 1
        if p == 0:
            r = i
            break
    return r


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def selection(node: cython.pointer(MCTSNode), c_puct: cython.double, n_vl: cython.int, move_indices: cython.pointer(cython.int),
              move_last: cython.pointer(cython.int)) -> cython.pointer(MCTSNode):
    # When we find a node which is not expanded. It may also happen that after this instruction, another thread starts expanding the node.
    # But we make sure to continue selection for this thread later.
    while node.expanded:
        # Getting a random roll
        r: cython.short = get_random_roll_sum()

        # Calculating the move start and move end
        ms: cython.short = 0
        me: cython.short = 0
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
        for i in range(ms, me):
            u[i] = c_puct * node.p[i] * sqrt_sum / (1 + node.n[i])
        mi: cython.int = 0
        max: cython.double = 0
        for i in range(ms, me):
            if max < (node.q[i] + u[i]):
                max = node.q[i] + u[i]
                mi = i
        mi = ms + mi
        move_indices[move_last[0]] = mi
        move_last[0] += 1
        free(u)

        # Adding virtual losses to node
        omp_set_lock(cython.address(node.access_lock))
        node.n[mi] += n_vl
        node.w[mi] -= n_vl
        omp_unset_lock(cython.address(node.access_lock))

        node = node.children[mi]

    return node


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def expansion(node: cython.pointer(MCTSNode), c_puct: cython.double, n_vl: cython.int, move_indices: cython.pointer(cython.int),
              move_last: cython.pointer(cython.int)) -> cython.pointer(MCTSNode):
    if not node.state.game_over:
        omp_set_lock(cython.address(node.access_lock))
        # If the node has not been expanded by another thread, expand it
        if not node.expanded:
            expand_mcts_node(node)
            # LOCK IS NOT RELEASED UNTIL p FOR node IS CALCULATED. THIS IS TO MAKE SURE OTHER THREADS WAIT FOR EXPANSION COMPLETION
        else:
            # Else, release lock immediately and resume from selection phase
            omp_unset_lock(cython.address(node.access_lock))
            node = selection(node, c_puct, n_vl, move_indices, move_last)
            node = expansion(node, c_puct, n_vl, move_indices, move_last)
    return node


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def mcts_job(j: cython.Py_ssize_t, model: ludoc.LudoModel, root: cython.pointer(MCTSNode), player: cython.short, c_puct: cython.double,
             n_vl: cython.int, eq: EvaluationQueue,
             max_depth: cython.int) -> cython.void:
    node: cython.pointer(MCTSNode) = root
    move_indices: cython.pointer(cython.int) = cython.cast(cython.pointer(cython.int),
                                                           calloc(max_depth, cython.sizeof(cython.int)))
    move_last: cython.int = 0

    # SELECTION
    node = selection(node, c_puct, n_vl, move_indices, cython.address(move_last))

    # EXPANSION
    node = expansion(node, c_puct, n_vl, move_indices, cython.address(move_last))

    # EVALUATION
    results: cython.pointer(cython.double) = cython.cast(cython.pointer(cython.double),
                                                         calloc(node.move_end - node.move_start,
                                                                cython.sizeof(cython.double)))
    if not node.state.game_over:
        future_ids: cython.pointer(cython.int) = cython.cast(cython.pointer(cython.int),
                                                             calloc(node.move_end - node.move_start,
                                                                    cython.sizeof(cython.int)))
        i: cython.Py_ssize_t
        for i in range(node.move_end - node.move_start):
            next_state: ludoc.StateStruct = node.children[i].state
            next_state.current_player = player
            future_ids[i] = add_to_eq(eq.queue_struct, next_state, cython.address(eq.insertion_lock))
        for i in range(node.move_end - node.move_start):
            while eq.queue_struct.queue[future_ids[i]].pending:
                sleep(0.0001)
            results[i] = eq.queue_struct.queue[future_ids[i]].result
    else:
        # TODO: Write winner finding logic
        pass

    # BACKUP

    free(results)
    free(move_indices)


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

    def expand_root(self):
        expand_mcts_node(self.root)

    def prune_root(self, roll: list):
        # Prunes the tree.
        r = sum(roll)
        ms: cython.short = 0
        me: cython.short = 0
        sum: cython.short = 0
        for i in range(19):
            if i == r:
                ms = sum
                me = ms + self.root.roll_num_moves[i]
                break
            sum += self.root.roll_num_moves[i]
        prune(self.root, ms, me)

    def mcts(self, simulations: cython.int, model: ludoc.LudoModel, player: cython.short, c_puct: cython.double,
             n_vl: cython.int, eq: EvaluationQueue,
             max_depth: cython.int):
        # Runs MCTS for simulations using prange
        i: cython.Py_ssize_t
        for i in prange(simulations, nogil=True):
            mcts_job(i, model, self.root, player, c_puct, n_vl, eq, max_depth)

    def take_move(self, move_idx: cython.short):
        # Takes the move, updates the tree and root.
        previous_root: cython.pointer(MCTSNode) = self.root
        self.root = previous_root.children[move_idx]
        previous_root.children[move_idx] = cython.NULL # Dereferencing the child before it gets freed by the next free node function call
        free_mcts_node(previous_root)

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
        queue.queue[queue.rear] = QN(data=data, pending=True, result=0.0)
        ret = queue.rear
        queue.rear = (queue.rear + 1) % queue.length
    omp_unset_lock(insertion_lock)
    return ret


@cython.cclass
class EvaluationQueue:
    queue_struct: cython.pointer(EQ)
    insertion_lock: omp_lock_t
    stop = cython.declare(cython.bint, visibility="public")

    def __init__(self, length: cython.int):
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

    def get_elems_pending(self, n_elems: cython.int) -> dict:
        accumulated_data = {}
        accum: cython.int = 0
        # Collect max(n_elems, number of left) Elements
        i: cython.int = self.queue_struct.front
        while i != self.queue_struct.rear and accum < n_elems:
            if self.queue_struct.queue[i].pending:
                # self.queue_struct.queue[i].data
                accumulated_data[i] = 0  # TODO: Translate from StateStruct to state repr in numpy
                accum += 1
            i = (i + 1) % self.queue_struct.length
        return accumulated_data

    def set_elems_result(self, results: dict):

        # Setting the results
        i: cython.int
        for i, res in results.items():
            self.queue_struct.queue[i].result = res
            self.queue_struct.queue[i].pending = False
        # Incrementing front so that queue is freed up
        while self.queue_struct.front != self.queue_struct.rear and not self.queue_struct.queue[
            self.queue_struct.front].pending:
            self.queue_struct.front = (self.queue_struct.front + 1) % self.queue_struct.length

    def set_stop(self):
        self.stop = True

    def __dealloc__(self):
        omp_destroy_lock(cython.address(self.insertion_lock))
        free(self.queue_struct.queue)
        free(self.queue_struct)
