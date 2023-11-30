import cython
from cython.cimports.libc.stdlib import free, calloc


@cython.cclass
class GameConfig:
    n_players = cython.declare(cython.short, visibility='public')
    player_colours: cython.p_short
    colour_player: cython.short[5]

    def __init__(self, player_colour_choices: list):
        self.n_players = cython.cast(cython.short, len(player_colour_choices))
        self.player_colours = cython.cast(cython.p_short, calloc(self.n_players, cython.sizeof(cython.short)))
        i: cython.Py_ssize_t
        for i in range(self.n_players):
            for colour in player_colour_choices[i]:
                if colour == "red":
                    self.player_colours[i] = self.player_colours[i] * 5 + 1
                elif colour == "green":
                    self.player_colours[i] = self.player_colours[i] * 5 + 2
                elif colour == "yellow":
                    self.player_colours[i] = self.player_colours[i] * 5 + 3
                elif colour == "blue":
                    self.player_colours[i] = self.player_colours[i] * 5 + 4
        self.colour_player[0] = 0
        for player, colours in enumerate(player_colour_choices):
            if "red" in colours:
                self.colour_player[1] = cython.cast(cython.short, player)
                break
        for player, colours in enumerate(player_colour_choices):
            if "green" in colours:
                self.colour_player[2] = cython.cast(cython.short, player)
                break
        for player, colours in enumerate(player_colour_choices):
            if "yellow" in colours:
                self.colour_player[3] = cython.cast(cython.short, player)
                break
        for player, colours in enumerate(player_colour_choices):
            if "blue" in colours:
                self.colour_player[4] = cython.cast(cython.short, player)
                break

    def __dealloc__(self):
        free(self.player_colours)


@cython.cclass
class LudoModel:
    config = cython.declare(GameConfig, visibility="public")
    stars: cython.p_short
    final_pos: cython.p_short
    colour_tracks: cython.p_short
    colour_bases: cython.p_short

    def __init__(self, config: GameConfig):
        self.config = config
        self.stars = cython.cast(cython.p_short, calloc(93, cython.sizeof(cython.short)))
        self.final_pos = cython.cast(cython.p_short, calloc(93, cython.sizeof(cython.short)))
        self.colour_bases = cython.cast(cython.p_short, calloc(5 * 4, cython.sizeof(cython.short)))
        self.colour_tracks = cython.cast(cython.p_short, calloc(5 * 57, cython.sizeof(cython.short)))
        i: cython.Py_ssize_t

        # RED
        for i in range(4):
            self.colour_bases[1 * 4 + i] = cython.cast(cython.short, i + 1)
        for i in range(52):
            self.colour_tracks[1 * 57 + i] = cython.cast(cython.short, i + 18)
        for i in range(6):
            self.colour_tracks[1 * 57 + i + 51] = cython.cast(cython.short, i + 69)

        # GREEN
        for i in range(4):
            self.colour_bases[2 * 4 + i] = cython.cast(cython.short, i + 5)
        for i in range(52):
            self.colour_tracks[2 * 57 + i] = cython.cast(cython.short, i + 31) if i + 31 <= 68 else cython.cast(
                cython.short, i - 21)
        for i in range(6):
            self.colour_tracks[2 * 57 + i + 51] = cython.cast(cython.short, i + 75)

        # YELLOW
        for i in range(4):
            self.colour_bases[3 * 4 + i] = cython.cast(cython.short, i + 9)
        for i in range(52):
            self.colour_tracks[3 * 57 + i] = cython.cast(cython.short, i + 44) if i + 44 <= 68 else cython.cast(
                cython.short, i - 8)
        for i in range(6):
            self.colour_tracks[3 * 57 + i + 51] = cython.cast(cython.short, i + 81)

        # BLUE
        for i in range(4):
            self.colour_bases[4 * 4 + i] = cython.cast(cython.short, i + 13)
        for i in range(52):
            self.colour_tracks[4 * 57 + i] = cython.cast(cython.short, i + 57) if i + 57 <= 68 else cython.cast(
                cython.short, i + 5)
        for i in range(6):
            self.colour_tracks[4 * 57 + i + 51] = cython.cast(cython.short, i + 87)

        for i in range(93):
            self.stars[i] = 1 if i in [18, 26, 31, 39, 44, 52, 57, 65] else 0
            self.final_pos[i] = 1 if i in [74, 80, 86, 92] else 0

    def __dealloc__(self):
        free(self.stars)
        free(self.final_pos)
        free(self.colour_bases)
        free(self.colour_tracks)


Block = cython.struct(pawns=cython.short, pos=cython.short, rigid=cython.bint)


StateStruct = cython.struct(
    n_players=cython.short,
    game_over=cython.bint,
    current_player=cython.short,
    num_more_moves=cython.short,
    dice_roll=cython.short,
    last_move_id=cython.short,
    pawn_pos=cython.p_short,
    num_blocks=cython.short,
    all_blocks=Block[16]
)


@cython.cfunc
def create_new_state(n_players: cython.short) -> StateStruct:
    pawn_pos: cython.p_short = cython.cast(cython.p_short, calloc(n_players * 93, cython.sizeof(cython.short)))
    state: StateStruct = StateStruct(n_players=n_players, game_over=False, current_player=0, num_more_moves=0, dice_roll=0, last_move_id=0, pawn_pos=pawn_pos, num_blocks=0)
    i: cython.Py_ssize_t
    for i in range(16):
        state.all_blocks[i] = Block(pawns=0, pos=cython.cast(cython.short, i), rigid=(i % 2 == 0))
    return state


@cython.cfunc
def free_state(state: StateStruct):
    free(state.pawn_pos)


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def copy_state(state: StateStruct) -> StateStruct:
    new_state: StateStruct = state
    pawn_pos: cython.p_short = cython.cast(cython.p_short, calloc(state.n_players * 93, cython.sizeof(cython.short)))
    i: cython.Py_ssize_t
    for i in range(state.n_players * 93):
        pawn_pos[i] = state.pawn_pos[i]
    new_state.pawn_pos = pawn_pos
    return new_state


@cython.cclass
class State:
    state_struct: StateStruct

    def __init__(self, n_players=0):
        self.state_struct: StateStruct = create_new_state(n_players)

    def set(self, state_dict):
        mappings = {
            "pawn": ["", "R1", "R2", "R3", "R4", "G1", "G2", "G3", "G4", "Y1", "Y2", "Y3", "Y4", "B1", "B2", "B3",
                     "B4"],
            "pos": ["", "RB1", "RB2", "RB3", "RB4", "GB1", "GB2", "GB3", "GB4", "YB1", "YB2", "YB3", "YB4", "BB1",
                    "BB2", "BB3", "BB4"]
                   + [f"P{i + 1}" for i in range(52)]
                   + ["RH1", "RH2", "RH3", "RH4", "RH5", "RH6", "GH1", "GH2", "GH3", "GH4", "GH5", "GH6", "YH1", "YH2",
                      "YH3", "YH4", "YH5", "YH6", "BH1", "BH2", "BH3", "BH4", "BH5", "BH6"]
        }
        dice_roll = 0
        roll = reversed(state_dict["dice_roll"])
        for r in roll:
            dice_roll = dice_roll * 7 + r

        pawn_pos = cython.cast(cython.p_short, calloc(state_dict['n_players'] * 93, cython.sizeof(cython.short)))
        for key in state_dict.keys():
            if "Player" in key:
                player_num = int(key[-1])
                for pawn, pos in state_dict[key].items():
                    pawn = mappings["pawn"].index(pawn)
                    pos = mappings["pos"].index(pos)
                    pawn_pos[player_num * 93 + pos] = pawn_pos[player_num * 93 + pos] * 17 + pawn
        state: StateStruct = StateStruct(n_players=state_dict["n_players"], game_over=state_dict["game_over"],
                                         current_player=state_dict["current_player"],
                                         num_more_moves=state_dict["num_more_moves"],
                                         dice_roll=dice_roll, last_move_id=state_dict["last_move_id"],
                                         pawn_pos=pawn_pos, num_blocks=len(state_dict["all_blocks"]))
        i: cython.Py_ssize_t
        for i in range(state.num_blocks):
            pawns = 0
            for p in state_dict["all_blocks"][i]["pawns"]:
                pawns = pawns * 17 + mappings["pawn"].index(p)
            state.all_blocks[i] = Block(pawns=pawns, pos=mappings["pos"].index(state_dict["all_blocks"][i]["pos"]),
                                        rigid=state_dict["all_blocks"][i]["rigid"])
        self.state_struct = state

    def get(self):
        mappings = {
            "pawn": ["", "R1", "R2", "R3", "R4", "G1", "G2", "G3", "G4", "Y1", "Y2", "Y3", "Y4", "B1", "B2", "B3",
                     "B4"],
            "pos": ["", "RB1", "RB2", "RB3", "RB4", "GB1", "GB2", "GB3", "GB4", "YB1", "YB2", "YB3", "YB4", "BB1",
                    "BB2", "BB3", "BB4"]
                   + [f"P{i + 1}" for i in range(52)]
                   + ["RH1", "RH2", "RH3", "RH4", "RH5", "RH6", "GH1", "GH2", "GH3", "GH4", "GH5", "GH6", "YH1", "YH2",
                      "YH3", "YH4", "YH5", "YH6", "BH1", "BH2", "BH3", "BH4", "BH5", "BH6"]
            }
        state = dict()
        s: StateStruct = self.state_struct
        state["n_players"] = s.n_players
        state["game_over"] = s.game_over
        state["current_player"] = s.current_player
        state["num_more_moves"] = s.num_more_moves
        state["dice_roll"] = []
        roll: cython.short = s.dice_roll
        while roll != 0:
            state["dice_roll"].append(roll % 7)
            roll //= 7
        state["last_move_id"] = s.last_move_id
        player: cython.short
        for player in range(s.n_players):
            k = dict()
            state[f"Player {player}"] = k
            pos: cython.short
            for pos in range(1, 93):
                pawns = []
                pawn: cython.short = s.pawn_pos[player * 93 + pos]
                while pawn != 0:
                    pawns.append(mappings["pawn"][pawn % 17])
                    pawn //= 17
                for p in pawns:
                    k[p] = mappings["pos"][pos]
        state["all_blocks"] = []
        i: cython.Py_ssize_t
        for i in range(s.num_blocks):
            pawns = []
            pawn: cython.short = s.all_blocks[i].pawns
            while pawn != 0:
                pawns.append(mappings["pawn"][pawn % 17])
                pawn //= 17
            state["all_blocks"].append(
                {"pawns": pawns, "pos": mappings["pos"][s.all_blocks[i].pos], "rigid": s.all_blocks[i].rigid})
        return state

    def get_copy(self):
        new_state: State = State()
        new_state.state_struct = copy_state(self.state_struct)
        return new_state

    def __dealloc__(self):
        free_state(self.state_struct)


@cython.cclass
class Ludo:
    state: StateStruct
    model: LudoModel
    winner: cython.short


