from copy import deepcopy
from random import randint

""" This file contains only stuff related to the implementation of the Ludo Engine """


class Player:
    """This class stores a particular player"""

    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return self.name == other.name

    def __repr__(self):
        return self.name

    def get_dict(self):
        return {"name": self.name}


class Pawn:
    """This class stores the id and colour of a pawn"""

    def __init__(self, id, colour):
        self.id = id
        self.colour = colour

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return f"PawnI{self.id}C{self.colour}"


class PawnBlock(Pawn):
    """This class stores a block of pawns. A block of pawns is also considered a pawn.
        Attributes:
            - id: Block Id
            - pawns: List of Pawn objects consisting the block
            - rigid: Whether the block can be broken in the next move or not
    """

    def __init__(self, pawns, id="", colour="", rigid=False):
        super().__init__(id, colour)
        self.pawns = pawns
        self.rigid = rigid

    def check_pawn_in_block(self, pawn):
        return pawn in self.pawns

    def check_pawn_ids(self, pawn_ids):
        for pawn_id in pawn_ids:
            if pawn_id not in [pawn.id for pawn in self.pawns]:
                return False
        return True

    def __eq__(self, other):
        return self.pawns == other.pawns

    def __repr__(self):
        return f"Block[{','.join([self.id] + [repr(pawn) for pawn in self.pawns])}]"


class GameConfig:
    """A GameConfig object describes the configuration of the game such as how many players are playing the game, which player has chosen which colour and so on. This object remains constant
    during the whole time the game engine runs.
        Attributes:
            - player_colour: Represents the colour choices of each player. It is a list of tuple of colours. Each element in the list represents a player and it's tuple represents the choice for his colours.
                    Note: No validation check is applied to verify the choice of colours. It is assumed correct colour choices are used
                    player_colour = [(RED, YELLOW), (GREEN, BLUE), ...]
            - players: List of Player objects
            - colour_player: An inverse mapping representing which colour corresponds to which player. Described as:
                 colour_player = {"RED": Player("Player1"), "GREEN": Player("Player2"), ...}
    """

    # Player_colour_choices = [(RED, YELLOW), (GREEN, BLUE)]
    def __init__(self, player_colour_choices):
        self.player_colour = player_colour_choices
        self.players = [Player(f"Player {i + 1}") for i in range(len(self.player_colour))]
        self.colour_player = {colour: self.players[i] for i, player in enumerate(self.player_colour) for colour
                              in player}

    def get_dict(self):
        return {"players": [player.get_dict() for player in self.players],
                "player_colour": [{self.players[i].name: self.player_colour[i]} for i in range(len(self.players))]}


class LudoModel:
    """ This class handles all game calculations and is meant to be used with MCTS to look forward in time. This object is supposed to be used as LudoObject.model
        Methods:
            - generate_next_state(state, move): This method returns the next state given the current state and move. Note: This method does not validate whether the move is applicable or not.
                                        It expects the move is a valid one. Do not send a move which is invalid. Unknown behaviour will be observed in that case. Moreover, this method does not change
                                        the "dice_roll" value and keeps it as it is since this method does not generate a new roll. New rolls are generated only by the Ludo class.
            - all_possible_moves(state): This method returns all possible validated moves from the current state. The return object is described as:
                             return [{"roll": [throw1, throw2,...], "moves": [[{Pawn1: Position}, {Pawn2: Position}, ...], ... ]}, ...]
    """


    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    BLUE = "blue"

    def __init__(self, config):
        self.config = config
        self.main_track = [f"P{i + 1}" for i in range(52)]
        self.tracks = {LudoModel.RED: self.main_track[1:52] + [f"RH{i + 1}" for i in range(6)],
                       LudoModel.GREEN: self.main_track[14:] + self.main_track[:13] + [f"GH{i + 1}" for i in range(6)],
                       LudoModel.YELLOW: self.main_track[27:] + self.main_track[:26] + [f"YH{i + 1}" for i in range(6)],
                       LudoModel.BLUE: self.main_track[40:] + self.main_track[:39] + [f"BH{i + 1}" for i in range(6)]}
        self.bases = {LudoModel.RED: [f"RB{i + 1}" for i in range(4)],
                      LudoModel.GREEN: [f"GB{i + 1}" for i in range(4)],
                      LudoModel.YELLOW: [f"YB{i + 1}" for i in range(4)],
                      LudoModel.BLUE: [f"BB{i + 1}" for i in range(4)]}
        self.stars = ["P2", "P15", "P28", "P41", "P10", "P23", "P36",
                      "P49"]  # First 4 are base entry stars and rest are in the way
        self.finale_positions = ["RH6", "GH6", "YH6", "BH6"]
        self.pawns = {LudoModel.RED: [Pawn(f"R{i + 1}", LudoModel.RED) for i in range(4)],
                      LudoModel.GREEN: [Pawn(f"G{i + 1}", LudoModel.GREEN) for i in range(4)],
                      LudoModel.YELLOW: [Pawn(f"Y{i + 1}", LudoModel.YELLOW) for i in range(4)],
                      LudoModel.BLUE: [Pawn(f"B{i + 1}", LudoModel.BLUE) for i in range(4)]}
        self.last_block_id = 0


    def get_colour_from_id(self, id):
        if id[0] == "R":
            return LudoModel.RED
        elif id[0] == "G":
            return LudoModel.GREEN
        elif id[0] == "Y":
            return LudoModel.YELLOW
        else:
            return LudoModel.BLUE


    def get_new_block_id(self):
        self.last_block_id += 1
        return f"BL{self.last_block_id}"

    def fetch_block_from_id(self, state, block_id):
        block = None
        for b in state["all_blocks"]:
            if b.id == block_id:
                block = b
                break
        return block

    def fetch_block_from_pawn_ids(self, state, pawn_ids):
        for block in state["all_blocks"]:
            if block.check_pawn_ids(pawn_ids):
                return block

    def find_next_possible_pawns(self, state):
        # Collect all next possible pawns
        current_player = self.config.players[state["current_player"]]
        next_possible_pawns = {"single_pawns": [], "block_pawns": []}
        # Single pawn forward
        for pawn_id in state[current_player.name]["single_pawn_pos"].keys():
            position = state[self.config.colour_player[self.get_colour_from_id(pawn_id)].name]["single_pawn_pos"][
                pawn_id]
            if position not in self.finale_positions:
                next_possible_pawns["single_pawns"].append([pawn_id, position])
        # Single pawn forward with block
        blocks = []
        for i in range(len(state[current_player.name]["single_pawn_pos"].items()) - 1):
            for j in range(i + 1, len(state[current_player.name]["single_pawn_pos"].items())):
                pawn1_id, pawn1_pos = list(state[current_player.name]["single_pawn_pos"].items())[i]
                pawn2_id, pawn2_pos = list(state[current_player.name]["single_pawn_pos"].items())[j]
                if pawn1_pos == pawn2_pos:
                    blocks.append([[pawn1_id, pawn2_id], pawn1_pos])
        next_possible_pawns["block_pawns"] = blocks
        # Block pawn forward
        for block_id, pos in state[current_player.name]["block_pawn_pos"].items():
            block = self.fetch_block_from_id(state, block_id)
            next_possible_pawns["block_pawns"].append([[pawn.id for pawn in block.pawns], pos])
        # Block pawn forward unblocked after star or unrigid block
        for block_id, block_pos in state[current_player.name]["block_pawn_pos"].items():
            block = self.fetch_block_from_id(state, block_id)
            if block_pos in self.stars or not block.rigid:
                for pawn in block.pawns:
                    next_possible_pawns["single_pawns"].append([pawn.id, block_pos])
        return next_possible_pawns

    def get_pawn_position(self, state, current_player, pawn_id):
        try:
            return state[current_player.name]["single_pawn_pos"][pawn_id]
        except:
            for block in state["all_blocks"]:
                for p in block.pawn:
                    if p.id == pawn_id:
                        return state[current_player.name]["block_pawn_pos"][block.id]

    def validate_pawn_move(self, state, roll, current_pos, pawn):
        # Calculate whether the move is valid given the state configuration and return the new positions of the pawns
        current_player = self.config.players[state["current_player"]]

        # TO VERIFY:
        # Single pawns:
        if isinstance(pawn, str):
            colour = self.get_colour_from_id(pawn)
            position = current_pos
            # Pawns only go to it's track only on 6 roll.
            if position in self.bases[colour] and roll != 6:
                return False, None
            if position in self.bases[colour] and roll == 6:
                return True, self.tracks[colour][0]
            # Pawns cannot jump beyond its track
            track = self.tracks[colour]
            index = track.index(position)
            if index + roll >= len(track):
                return False, None
            # Pawns cannot jump over other pawn blocks except pos is a home star
            other_players = [player for idx, player in enumerate(self.config.players) if idx != state["current_player"]]
            for i in range(index + 1, index + roll):
                pos = track[i]
                for other_player in other_players:
                    for _, block_pos in state[other_player.name]["block_pawn_pos"].items():
                        if pos == block_pos and pos not in self.stars[:4]:
                            return False, None
            # Pawns cannot move to a destination if the same player's one block and one single pawn is present except home star
            destination = track[index + roll]
            for _, block_pos in state[current_player.name]["block_pawn_pos"].items():
                if destination == block_pos and destination not in self.stars[:4]:
                    for _, single_pos in state[current_player.name]["single_pawn_pos"].items():
                        if destination == single_pos:
                            return False, None
        # Block Pawns:
        else:
            # block_id = self.fetch_block_from_pawn_ids(state, pawn).id
            # Move is possible only if roll%2 == 0
            if roll % 2 != 0:
                return False, None
            pawn1_id, pawn2_id = pawn
            position = current_pos
            pawn1_colour = self.get_colour_from_id(pawn1_id)
            pawn2_colour = self.get_colour_from_id(pawn2_id)
            pawn1_track = self.tracks[pawn1_colour]
            pawn2_track = self.tracks[pawn2_colour]
            # Block Pawns cannot jump beyond their track
            pawn1_index = pawn1_track.index(position)
            if pawn1_index + roll // 2 >= len(pawn1_track) or pawn2_track.index(position) + roll // 2 >= len(
                    pawn2_track):
                return False, None
            # Move is possible only if both BlockPawns land at the same place after moving
            if pawn1_track[pawn1_track.index(position) + roll // 2] != pawn2_track[
                pawn2_track.index(position) + roll // 2]:
                return False, None
            # Block Pawns cannot jump over other pawn blocks except pos is a home star
            other_players = [player for idx, player in enumerate(self.config.players) if idx != state["current_player"]]
            for i in range(pawn1_index + 1, pawn1_index + roll // 2):
                pos = pawn1_track[i]
                for other_player in other_players:
                    for _, block_pos in state[other_player.name]["block_pawn_pos"].items():
                        if pos == block_pos and pos not in self.stars[:4]:
                            return False, None
            # Block Pawns cannot move to a destination if the same player's another block is present
            destination = pawn1_track[pawn1_index + roll // 2]
            for _, block_pos in state[current_player.name]["block_pawn_pos"].items():
                if destination == block_pos:
                    return False, None
        return True, destination

    def __generate_next_state(self, state, roll, current_pos, pawn):
        state = deepcopy(state)
        num_more_moves = 0
        current_player = self.config.players[state["current_player"]]
        # If single pawn, find next position and update it.
        if isinstance(pawn, str):
            colour = self.get_colour_from_id(pawn)
            position = current_pos
            track = self.tracks[colour]
            try:
                index = track.index(position)
            except:
                index = -6
            destination = track[index + roll]

            state[current_player.name]["single_pawn_pos"][pawn] = destination

            # If pawn is in a block, dissolve the block, leave the other pawn in old position
            for block in state["all_blocks"]:
                if pawn in [p.id for p in block.pawns]:
                    old_pos = state[current_player.name]["block_pawn_pos"][block.id]
                    state[current_player.name]["block_pawn_pos"].pop(block.id)
                    other_pawn_id = block.pawns[0].id if block.pawns[0].id != pawn else block.pawns[1].id
                    state[current_player.name]["single_pawn_pos"][other_pawn_id] = old_pos
                    state["all_blocks"].remove(block)
                    break

            # If at current position two pawns are present and current position is not home star, block them up (non-rigid)
            pawns_at_current = [p_id for p_id, pos in state[current_player.name]["single_pawn_pos"].items() if
                                pos == position and pos not in self.stars[:4]]
            if len(pawns_at_current) >= 2:
                state[current_player.name]["single_pawn_pos"].pop(pawns_at_current[0])
                state[current_player.name]["single_pawn_pos"].pop(pawns_at_current[1])
                block = PawnBlock([p for p in
                                   self.pawns[LudoModel.RED] + self.pawns[LudoModel.GREEN] + self.pawns[LudoModel.YELLOW] +
                                   self.pawns[LudoModel.BLUE] if p.id in pawns_at_current[:2]], self.get_new_block_id())
                state["all_blocks"].append(block)
                state[current_player.name]["block_pawn_pos"][block.id] = position

            # If another single pawn of other player is present at destination position (except stars), capture it by sending it back to its base
            other_players = [player for idx, player in enumerate(self.config.players) if idx != state["current_player"]]
            for other_player in other_players:
                for pawn_id, pos in state[other_player.name]["single_pawn_pos"].items():
                    if destination == pos and destination not in self.stars:
                        state[other_player.name]["single_pawn_pos"][pawn_id] = \
                            self.bases[self.get_colour_from_id(pawn_id)][int(pawn_id[1:]) - 1]
                        num_more_moves += 1
                        break

            # If another single pawn of same player is present at destination position, block it with other pawn by default except the home star positions and finale position
            for pawn_id, pos in state[current_player.name]["single_pawn_pos"].items():
                if destination == pos and pawn_id != pawn and destination not in self.stars[:4] + self.finale_positions:
                    state[current_player.name]["single_pawn_pos"].pop(pawn_id)
                    state[current_player.name]["single_pawn_pos"].pop(pawn)
                    block = PawnBlock([p for p in
                                       self.pawns[LudoModel.RED] + self.pawns[LudoModel.GREEN] + self.pawns[LudoModel.YELLOW] +
                                       self.pawns[LudoModel.BLUE] if p.id in [pawn_id, pawn]], self.get_new_block_id())
                    state["all_blocks"].append(block)
                    state[current_player.name]["block_pawn_pos"][block.id] = destination
                    break

            # If destination is finale and not all other pawns in finale position, give another move
            if destination in self.finale_positions and len(
                    [pos for pawn_id, pos in state[current_player.name]["single_pawn_pos"].items() if
                     pos not in self.finale_positions] + [pos for b_id, pos in
                                                          state[current_player.name]["block_pawn_pos"].items() if
                                                          pos not in self.finale_positions]) > 0:
                num_more_moves += 1

        # If Block pawn, find next position and update it.
        else:
            pawn1_id, _ = pawn
            position = current_pos
            pawn1_colour = self.get_colour_from_id(pawn1_id)
            pawn1_track = self.tracks[pawn1_colour]
            index = pawn1_track.index(position)
            destination = pawn1_track[index + roll // 2]

            if position in self.stars[:4]:
                block = PawnBlock([p for p in
                                   self.pawns[LudoModel.RED] + self.pawns[LudoModel.GREEN] + self.pawns[LudoModel.YELLOW] +
                                   self.pawns[LudoModel.BLUE] if p.id in pawn], self.get_new_block_id())
                state["all_blocks"].append(block)
            else:
                block = self.fetch_block_from_pawn_ids(state, pawn)
            block_id = block.id
            state[current_player.name]["block_pawn_pos"][block_id] = destination

            # If another Block pawn of other player is present at destination position (except stars), capture them by breaking the block and sending them back to their respective bases
            other_players = [player for idx, player in enumerate(self.config.players) if idx != state["current_player"]]
            for other_player in other_players:
                for b_id, pos in state[other_player.name]["block_pawn_pos"].items():
                    if destination == pos and destination not in self.stars:
                        b = self.fetch_block_from_id(state, b_id)
                        state["all_blocks"].remove(b)
                        state[other_player.name]["block_pawn_pos"].pop(b_id)
                        for p in b.pawns:
                            state[other_player.name]["single_pawn_pos"][p.id] = \
                                self.bases[self.get_colour_from_id(p.id)][int(p.id[1:]) - 1]
                        num_more_moves += 2
                        break

            # If destination is home or finale position , break the block into single pawns
            if destination in self.finale_positions + self.stars[:4]:
                state["all_blocks"].remove(block)
                state[current_player.name]["block_pawn_pos"].pop(block_id)
                for p in block.pawns:
                    state[current_player.name]["single_pawn_pos"][p.id] = destination
            # Elif destination is an intermediate star, make the block not rigid
            elif destination in self.stars[4:]:
                block.rigid = False
            # Else, remove the single pawns of the block because the block will be rigid
            else:
                block.rigid = True
                for p in block.pawns:
                    try:
                        state[current_player.name]["single_pawn_pos"].pop(p.id)
                    except:
                        # Ignore if block is already rigid
                        pass

            # If destination is finale and not all other pawns in finale position, give two more move
            if destination in self.finale_positions and len(
                    [pos for pawn_id, pos in state[current_player.name]["single_pawn_pos"].items() if
                     pos not in self.finale_positions] + [pos for pawn_id, pos in state[current_player.name]["block_pawn_pos"].items() if
                     pos not in self.finale_positions]) > 0:
                num_more_moves += 2

        return state, num_more_moves

    def generate_next_state(self, state, move):
        if state["num_more_moves"] > 0:
            state["num_more_moves"] -= 1
        if move != [[]]:
            total_moves = 0
            for m, r in zip(move, state["dice_roll"]):
                state, num_more_moves = self.__generate_next_state(state, r, m[1], m[0])
                total_moves += num_more_moves
            state["num_more_moves"] = total_moves
        # Update last move_id
        state["last_move_id"] += 1
        # Change the turn
        if state["num_more_moves"] == 0:
            state["current_player"] = (state["current_player"] + 1) % len(self.config.players)
        # Check game over or not by evaluating if all other players have completed
        game_over = True
        for colour, player in self.config.colour_player.items():
            if player != self.config.players[state["current_player"]]:
                for pawn in self.pawns[colour]:
                    try:
                        if state[player.name]["single_pawn_pos"][pawn.id] not in self.finale_positions:
                            game_over = False
                    except:
                        # If pawn is blocked with other, that means the game is not over for the player
                        game_over = False
        state["game_over"] = game_over
        return state

    def generate_and_validate_moves(self, state, roll, selected_pawns):
        state = deepcopy(state)
        valid_moves = []
        if len(roll) > 0:
            # find out all possible movable pawns
            next_possible_pawns = self.find_next_possible_pawns(state)
            # Validate whether moving that pawn is possible or not for roll[0]
            # valid_pawn_selections = []
            for pawn, current_pos in next_possible_pawns["single_pawns"] + next_possible_pawns["block_pawns"]:
                valid, destination_pos = self.validate_pawn_move(state, roll[0], current_pos, pawn)
                # If valid move, generate new state by moving pawn and recursively find out next valid pawn movements for roll[1:]
                if valid:
                    sp = deepcopy(selected_pawns)
                    sp.append([pawn, current_pos, destination_pos])
                    # valid_pawn_selections.append(sp)
                    next_state = self.__generate_next_state(state, roll[0], current_pos, pawn)[0]

                    # If all pawns of the player are in finale positions, send back selected pawns
                    try:
                        for colour in self.config.player_colour[next_state["current_player"]]:
                            for pawn in self.pawns[colour]:
                                if next_state[self.config.players[next_state["current_player"]].name]["single_pawn_pos"][pawn.id] not in self.finale_positions:
                                    break
                            else:
                                return [sp]
                    except:
                        # If any error comes up, it means not all pawns are in finale positions
                        pass

                    for moves in self.generate_and_validate_moves(next_state, roll[1:], sp):
                        valid_moves.append(moves)
            return valid_moves
        else:
            return [selected_pawns]

    def all_possible_moves(self, state):
        # Calculates all possible moves by a player before dice roll
        state = deepcopy(state)
        possible_rolls = [[i] for i in range(1, 6)] + [[6, i] for i in range(1, 6)] + [[6, 6, i] for i in range(1, 6)]

        # possible_moves = [{"roll": [], "moves": [[{Pawn1: Position}, {Pawn2: Position}, ...], ... ]}, ...]
        possible_moves = []
        for roll in possible_rolls:
            validated_moves = self.generate_and_validate_moves(state, roll, [])
            possible_moves.append({"roll": roll, "moves": validated_moves})

        return possible_moves


class Ludo:
    """ This is the actual game engine which stores the state of the game
     Attributes:
        - model: This object has stateless functions to perform all calculations for the game.
        - state: Represents the current state of the game. It is a dictionary as described below :
                state = {
                    "game_over": False (Has the game ended or not),
                    "current_player": 0 (index of player in config object),
                    "num_more_moves": 0, (How many more moves of the current player is left)
                    "dice_roll": [] (result of recent dice roll, empty means dice is yet to be rolled),
                    "last_move_id": 0, (What was the last move id: used to accept a new move based on last_move_id)
                    "player i": {"single_pawn_pos": {"pawn1": "position", ...}, "block_pawn_pos": {"blocked_pawn1": "position"}},
                    ...,
                    "all_blocks": [] (all blocks that are currently present on the board)
                }
        - all_current_moves: List of all possible moves corresponding to a particular roll. Described below:
                all_current_moves = [{"roll": [throw1, throw2,...], "moves": [[{Pawn1: Position}, {Pawn2: Position}, ...], ... ]}, ...]

    Methods:
        - __init__(config): Constructor to create the engine with a GameConfig object. See doc string of GameConfig class
        - turn(move, move_id): Takes a move. "move_id" is presented to verify no move is taken twice.

    """

    def __init__(self, config):
        self.model = LudoModel(config)

        # Creating initial state
        roll = self.generate_dice_roll()

        self.state = {"game_over": False, "current_player": 0, "num_more_moves": 0, "dice_roll": roll,
                      "last_move_id": 0}

        for i, player in enumerate(config.players):
            pawns = {}
            for colour in config.player_colour[i]:
                for pawn, pos in zip(self.model.pawns[colour], self.model.bases[colour]):
                    pawns[pawn.id] = pos
            self.state[player.name] = {"single_pawn_pos": pawns, "block_pawn_pos": {}}
        self.state["all_blocks"] = []

        self.all_current_moves = self.model.all_possible_moves(self.state)

    def generate_dice_roll(self):
        roll = []
        for i in range(3):
            rnd = randint(1, 6)
            roll.append(rnd)
            if rnd != 6:
                break
        return roll

    def turn(self, move, move_id):
        # Take the move and create next state
        if move_id == self.state["last_move_id"] + 1:
            self.state = self.model.generate_next_state(self.state, move)
            if not self.state["game_over"]:
                # cache all possible next moves
                self.all_current_moves = self.model.all_possible_moves(self.state)
                # Generate new dice roll
                roll = self.generate_dice_roll()

                self.state["dice_roll"] = roll
                print(self.state, [{"roll": move["roll"], "moves": len(move["moves"])} for move in self.all_current_moves])
                print(f"player {self.state['current_player']}, roll {roll}")



