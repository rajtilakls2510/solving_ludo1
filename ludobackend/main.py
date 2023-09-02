from copy import deepcopy


class Player:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return self.name == other.name

    def __repr__(self):
        return self.name


class Pawn:
    def __init__(self, id, colour):
        self.id = id
        self.colour = colour

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return f"PawnI{self.id}C{self.colour}"


class PawnBlock(Pawn):
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
        return f"Block[{','.join([repr(pawn) for pawn in self.pawns])}]"


class GameConfig:

    # Player_colour_choices = [(RED, YELLOW), (GREEN, BLUE)]
    def __init__(self, player_colour_choices):
        self.player_colour = player_colour_choices
        self.players = [Player(f"Player {i + 1}") for i in range(len(self.player_colour))]
        self.colour_player = {colour: self.players[i] for i, player in enumerate(self.player_colour) for colour
                              in player}


class Ludo:
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    BLUE = "blue"

    def __init__(self, config):
        self.config = config
        self.main_track = [f"P{i + 1}" for i in range(52)]
        self.tracks = {Ludo.RED: self.main_track[1:52] + [f"RH{i + 1}" for i in range(6)],
                       Ludo.GREEN: self.main_track[14:] + self.main_track[:13] + [f"GH{i + 1}" for i in range(6)],
                       Ludo.YELLOW: self.main_track[27:] + self.main_track[:26] + [f"YH{i + 1}" for i in range(6)],
                       Ludo.BLUE: self.main_track[40:] + self.main_track[:39] + [f"BH{i + 1}" for i in range(6)]}
        self.bases = {Ludo.RED: [f"RB{i + 1}" for i in range(4)],
                      Ludo.GREEN: [f"GB{i + 1}" for i in range(4)],
                      Ludo.YELLOW: [f"YB{i + 1}" for i in range(4)],
                      Ludo.BLUE: [f"BB{i + 1}" for i in range(4)]}
        self.stars = ["P2", "P15", "P28", "P41", "P10", "P23", "P36",
                      "P49"]  # First 4 are base entry stars and rest are in the way
        self.finale_positions = ["RH6", "GH6", "YH6", "BH6"]
        self.pawns = {Ludo.RED: [Pawn(f"R{i + 1}", Ludo.RED) for i in range(4)],
                      Ludo.GREEN: [Pawn(f"G{i + 1}", Ludo.GREEN) for i in range(4)],
                      Ludo.YELLOW: [Pawn(f"Y{i + 1}", Ludo.YELLOW) for i in range(4)],
                      Ludo.BLUE: [Pawn(f"B{i + 1}", Ludo.BLUE) for i in range(4)]}

        # Creating initial state
        """ state = {
            "current_player": 0 (index of player in config object), 
            dice_roll: [] (result of recent dice roll, empty means dice is yet to be rolled),
            "player i": {"single_pawn_pos": {"pawn1": "position", ...}, "block_pawn_pos": {"blocked_pawn1": "position"}},
            ...,
            "all_blocks": [] (all blocks that are currently present on the board)
        }"""

        self.state = {"current_player": 0, "dice_roll": []}

        for i, player in enumerate(config.players):
            pawns = {}
            for colour in config.player_colour[i]:
                for pawn, pos in zip(self.pawns[colour], self.bases[colour]):
                    pawns[pawn.id] = pos
            self.state[player.name] = {"single_pawn_pos": pawns, "block_pawn_pos": {}}
        self.state["all_blocks"] = []

        # print(self.state)
        self.last_block_id = 0

    def get_colour_from_id(self, id):
        if id[0] == "R":
            return ludo.RED
        elif id[0] == "G":
            return ludo.GREEN
        elif id[0] == "Y":
            return ludo.YELLOW
        else:
            return ludo.BLUE

    def turn(self):
        # TODO: Whenever a pawn lands on a pawn of the same player, make it a block by default except the home start positions and finale position
        pass

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
        # Block pawn forward unblocked after star
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
            # Pawns cannot jump over other pawn blocks
            other_players = [player for idx, player in enumerate(self.config.players) if idx != state["current_player"]]
            for i in range(index + 1, index + roll):
                pos = track[i]
                for other_player in other_players:
                    for _, block_pos in state[other_player.name]["block_pawn_pos"].items():
                        if pos == block_pos:
                            return False, None
            # Pawns cannot move to a destination if the same player's one block and one single pawn is present
            destination = track[index + roll]
            for _, block_pos in state[current_player.name]["block_pawn_pos"].items():
                if destination == block_pos:
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
            # Block Pawns cannot jump over other pawn blocks
            other_players = [player for idx, player in enumerate(self.config.players) if idx != state["current_player"]]
            for i in range(pawn1_index + 1, pawn1_index + roll // 2):
                pos = pawn1_track[i]
                for other_player in other_players:
                    for _, block_pos in state[other_player.name]["block_pawn_pos"].items():
                        if pos == block_pos:
                            return False, None
            # Block Pawns cannot move to a destination if the same player's another block is present
            destination = pawn1_track[pawn1_index + roll // 2]
            for _, block_pos in state[current_player.name]["block_pawn_pos"].items():
                if destination == block_pos:
                    return False, None
        return True, destination

    def generate_next_state(self, state, roll, current_pos, pawn):
        state = deepcopy(state)
        captured = False
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

            # If another single pawn of other player is present at destination position (except stars), capture it by sending it back to its base
            other_players = [player for idx, player in enumerate(self.config.players) if idx != state["current_player"]]
            for other_player in other_players:
                for pawn_id, pos in state[other_player.name]["single_pawn_pos"].items():
                    if destination == pos and destination not in self.stars:
                        state[other_player.name]["single_pawn_pos"][pawn_id] = \
                            self.bases[self.get_colour_from_id(pawn_id)][int(pawn_id[1:])]
                        captured = True
                        break

            # If another single pawn of same player is present at destination position (except base stars), block it with other pawn by default except the home start positions and finale position
            for pawn_id, pos in state[current_player.name]["single_pawn_pos"].items():
                if destination == pos and pawn_id != pawn and destination not in self.stars[:4] + self.finale_positions:
                    state[current_player.name]["single_pawn_pos"].pop(pawn_id)
                    state[current_player.name]["single_pawn_pos"].pop(pawn)
                    block = PawnBlock([p for p in
                                       self.pawns[Ludo.RED] + self.pawns[Ludo.GREEN] + self.pawns[Ludo.YELLOW] +
                                       self.pawns[Ludo.BLUE] if p.id in [pawn_id, pawn]], self.get_new_block_id())
                    state["all_blocks"].append(block)
                    state[current_player.name]["block_pawn_pos"][block.id] = destination
                    break

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
                                   self.pawns[Ludo.RED] + self.pawns[Ludo.GREEN] + self.pawns[Ludo.YELLOW] +
                                   self.pawns[Ludo.BLUE] if p.id in pawn], self.get_new_block_id())
                state["all_blocks"].append(block)
            else:
                block = self.fetch_block_from_pawn_ids(state, pawn)
            block_id = block.id
            block.rigid = True
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
                                self.bases[self.get_colour_from_id(p.id)][int(p.id[1:])]
                        captured = True
                        break

            # If destination is finale position, break the block into single pawns
            if destination in self.finale_positions:
                block = self.fetch_block_from_id(state, block_id)
                state["all_blocks"].remove(block)
                state[current_player.name]["block_pawn_pos"].pop(block_id)
                for p in block.pawns:
                    state[current_player.name]["single_pawn_pos"][p.id] = destination

        return state, captured

    def generate_and_validate_moves(self, state, roll, selected_pawns):

        valid_moves = []
        if roll:
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
                    next_state = self.generate_next_state(state, roll[0], current_pos, pawn)[0]
                    for moves in self.generate_and_validate_moves(next_state, roll[1:], sp):
                        valid_moves.append(moves)
            return valid_moves
        else:
            return [selected_pawns]

    def all_possible_moves(self, state):
        # Calculates all possible moves by a player before dice roll

        possible_rolls = [[i] for i in range(1, 6)] + [[6, i] for i in range(1, 6)] + [[6, 6, i] for i in range(1, 6)]

        # possible_moves = [{"roll": [], "moves": [[{Pawn1: Position}, {Pawn2: Position}, ...], ... ]}, ...]
        possible_moves = []
        for roll in possible_rolls:
            validated_moves = self.generate_and_validate_moves(state, roll, [])
            possible_moves.append({"roll": roll, "moves": validated_moves})
        print(possible_moves)
        print([[rm["roll"], len(rm["moves"])] for rm in possible_moves])


ludo = Ludo(GameConfig([(Ludo.RED, Ludo.YELLOW), (Ludo.BLUE, Ludo.GREEN)]))

state = {"current_player": 0, "dice_roll": [],
         ludo.config.players[0].name: {"single_pawn_pos": {"R1": "RB1", "Y1": "YB1", "Y2": "P28", "Y4": "YH3"},
                                       "block_pawn_pos": {"BL1": "P4", "BL2": "P23"}},
         ludo.config.players[1].name: {
             "single_pawn_pos": {"G1": "GB1", "G2": "P24", "G3": "P35", "G4": "P41", "B1": "BB1", "B3": "P5",
                                 "B4": "BH2"},
             "block_pawn_pos": {"BL3": "P5"}},
         "all_blocks": [
             PawnBlock(
                 [pawn for id in ["R3", "R4"] for pawn in ludo.pawns[ludo.get_colour_from_id(id)] if pawn.id == id],
                 "BL1", rigid=True),
             PawnBlock(
                 [pawn for id in ["R2", "Y3"] for pawn in ludo.pawns[ludo.get_colour_from_id(id)] if pawn.id == id],
                 "BL2"),
             PawnBlock(
                 [pawn for id in ["B2", "B3"] for pawn in ludo.pawns[ludo.get_colour_from_id(id)] if pawn.id == id],
                 "BL3", rigid=True),
         ],
         }
ludo.all_possible_moves(state)
