import base64
import threading
import time
import traceback
from random import choices
import numpy as np
from copy import deepcopy
import tensorflow as tf


class MCTNode:
    def __init__(self, state, players, model, parent):
        """Creates an MCTS node after expanding its moves
        Args:
            - state: The game state corresponding to the node. ["dice_roll" is ignored]
            - players: List of player objects present in game_config
            - model: The model of the ludo game
            - parent: The reference to the parent node so that backup becomes easy
            """
        self.state = state
        self.players = players
        self.model = model
        self.parent = parent
        self.available_moves = []
        self.stats = {player.name: {} for player in self.players}
        self.children = []
        self.expanded = False  # By default, make the node expanded if game is over at this state
        self.expansion_event = threading.Event()
        self.expansion_event.set()

    def expand(self):
        """Expands the node and creates stats and children nodes. Returns all next states"""

        # Generate all possible moves
        valid_moves = []
        if not self.state["game_over"]:
            moves = self.model.all_possible_moves(self.state)
            for d in moves:
                if len(d["moves"]) > 0:
                    for move in d["moves"]:
                        valid_moves.append({"roll": d["roll"], "move": move})
                else:
                    valid_moves.append({"roll": d["roll"], "move": [[]]})
        self.available_moves = valid_moves

        # Initialize the statistics for each player
        for player in self.players:
            self.stats[player.name] = {
                "P": np.random.random(size=len(self.available_moves)),
                "N": np.ones(shape=(len(self.available_moves),)),
                "W": np.zeros(shape=(len(self.available_moves),))
            }

        # Generating next states
        next_states = []
        roll = self.state["dice_roll"]
        for move in self.available_moves:
            self.state["dice_roll"] = move["roll"]
            next_states.append(self.model.generate_next_state(self.state, move["move"]))
        self.expanded = True
        self.state["dice_roll"] = roll

        # Generating next nodes
        self.children = [MCTNode(state, self.players, self.model, self) for state in next_states]

        return next_states

    def prune(self, from_index, to_index):
        """Prunes the tree according to indices of moves.
            Args:
                - from_index (included): The index from which moves have to be kept
                - to_index (excluded): The index to which moves have to be kept
        """
        # Prune moves and children
        new_moves = []
        new_children = []
        for index, move in enumerate(self.available_moves):
            if from_index <= index < to_index:
                new_moves.append(move)
                if self.expanded:
                    new_children.append(self.children[index])
        self.available_moves = new_moves
        self.children = new_children

        # Prune stats of players
        for player in self.players:
            self.stats[player.name]["P"] = self.stats[player.name]["P"][from_index: to_index]
            self.stats[player.name]["N"] = self.stats[player.name]["N"][from_index: to_index]
            self.stats[player.name]["W"] = self.stats[player.name]["W"][from_index: to_index]


def softmax(a, temp=0.1):
    if temp == 0:
        temp += 0.001
    a = np.exp(a - np.max(a))
    return np.exp(a / temp) / np.sum(np.exp(a / temp))


def mcts_job(num, root, player, evaluator_conn, c_puct, n_vl, prior_temp):
    """This function performs the MCTS job of 4 steps and returns the depth reached by the selection step"""
    # print(f"{num} Selecting")
    try:
        node = root

        # SELECTION
        move_indices = []
        chk1 = time.perf_counter()
        node.expansion_event.wait() # Before attending to any node, wait if another thread is expanding it
        while node.expanded:
            # Applying chance on SELECTION
            rolls = [[i] for i in range(1, 6)] + [[6, i] for i in range(1, 6)] + [[6, 6, i] for i in range(1, 6)]
            roll = choices(rolls)
            
            from_index, to_index = 0, len(node.available_moves)
            found = False
            for index, move_dict in enumerate(node.available_moves):
                if move_dict["roll"] == roll and not found:
                    from_index = index
                    found = True
                elif move_dict["roll"] != roll and found:
                    to_index = index
                    found = False
                    break
            if from_index >= to_index:
                print(f"{num} from_index: {from_index} to_index: {to_index}")
            p = node.stats[player.name]["P"][from_index:to_index]
            n = node.stats[player.name]["N"][from_index:to_index]
            w = node.stats[player.name]["W"][from_index:to_index]

            # Selecting a move
            u = c_puct * p * (np.sqrt(np.sum(n)) / (1.0 + n))
            chosen_move_index = np.argmax(w / n + u)

            # Applying virtual losses
            n[chosen_move_index] += n_vl
            w[chosen_move_index] -= n_vl

            move_indices.append(chosen_move_index + from_index)
            node = node.children[chosen_move_index + from_index]
            node.expansion_event.wait() # Before attending to any node, wait if another thread is expanding it
        chk2 = time.perf_counter()
        # EXPANSION
        if not node.expansion_event.is_set():
            # In the unfortunate case that a thread has already got passed event.wait() while another thread is expanding the same node, backup the virtual losses and discard the thread
            node = node.parent
            move_indices.reverse()

            for move_index in move_indices:
                node.stats[player.name]["N"][move_index] -= n_vl
                node.stats[player.name]["W"][move_index] += n_vl
                node = node.parent
            print(f"{num} Unfortunate Ending! Selection: {chk2 - chk1}")
            return 0
        node.expansion_event.clear()
        # print(f"{num} Expanding. Selection: {chk2 - chk1}")
        if not node.state["game_over"]:
            next_states = node.expand()
        node.expansion_event.set()
        chk3 = time.perf_counter()
        # EVALUATION
        # print(f"{num} Evaluating. Expansion: {chk3 - chk2}")
        result = 0
        if not node.state["game_over"]:
            next_states = [deepcopy(state) for state in next_states]
            for state in next_states:
                state["current_player"] = node.state["current_player"]
            states_serialized = base64.b64encode(
                tf.io.serialize_tensor(
                    tf.stack([node.model.state_to_repr(state) for state in next_states])).numpy()).decode(
                'ascii')
            result = tf.io.parse_tensor(base64.b64decode(evaluator_conn.root.evaluate(player.name, states_serialized)),
                                        out_type=tf.float32).numpy()
        else:
            # Finding winner and setting result according to it
            winner = None
            for p in node.model.config.players:
                not_finale = False
                for colour in p.colours:
                    for pawn in node.model.pawns[colour]:
                        try:
                            if node.state[p.name]["single_pawn_pos"][pawn.id] not in node.model.finale_positions:
                                not_finale = True
                        except:
                            not_finale = True
                if not not_finale:
                    winner = p
                    break
            if winner:
                result = 1 if winner == player else -1
        chk4 = time.perf_counter()
        # BACKUP
        # print(f"{num} Backup. Evaluation: {chk4 - chk3}")
        p = softmax(result, temp=prior_temp)
        v = np.sum(p * result)
        node.stats[player.name]["P"] = p
        node = node.parent
        move_indices.reverse()

        for move_index in move_indices:
            player_multipler = 1 if node.model.config.players[node.state["current_player"]] == player else -1
            node.stats[player.name]["N"][move_index] += 1 - n_vl
            node.stats[player.name]["W"][move_index] += (player_multipler * v) + n_vl
            node = node.parent
        chk5 = time.perf_counter()
        # print(f"{num} Num moves: {len(move_indices)} Ending: {chk5 - chk1}")
        return len(move_indices)
    except Exception as e:
        # print(f"E: {str(e)}")
        #traceback.print_exc()
        return -1
