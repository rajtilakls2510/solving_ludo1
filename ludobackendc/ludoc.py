
import cython
from cython.cimports.libc.stdlib import free, calloc


@cython.cclass
class GameConfig:
    n_players: cython.short
    player_colours: cython.p_short
    colour_player: cython.short[5]

    def __init__(self, player_colour_choices: list):
        self.n_players = cython.cast(cython.short, len(player_colour_choices))
        self.player_colours = cython.cast(cython.p_short, calloc(self.n_players, cython.sizeof(cython.short)))
        i: cython.Py_ssize_t
        for i in range(self.n_players):
            for colour in player_colour_choices[i]:
                if colour == "red":
                    self.player_colours[i] = self.player_colours[i]*5 + 1
                elif colour == "green":
                    self.player_colours[i] = self.player_colours[i]*5 + 2
                elif colour == "yellow":
                    self.player_colours[i] = self.player_colours[i]*5 + 3
                elif colour == "blue":
                    self.player_colours[i] = self.player_colours[i]*5 + 4
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
    config: GameConfig
    stars: cython.p_short
    final_pos: cython.p_short
    colour_tracks: cython.p_short
    colour_bases: cython.p_short

    def __init__(self, config: GameConfig):
        self.config = config
        self.stars = cython.cast(cython.p_short, calloc(93, cython.sizeof(cython.short)))
        self.final_pos = cython.cast(cython.p_short, calloc(93, cython.sizeof(cython.short)))
        self.colour_bases = cython.cast(cython.p_short, calloc(5*4, cython.sizeof(cython.short)))
        self.colour_tracks = cython.cast(cython.p_short, calloc(5*57, cython.sizeof(cython.short)))
        i: cython.Py_ssize_t

        # RED
        for i in range(4):
            self.colour_bases[1*4 + i] = cython.cast(cython.short, i + 1)
        for i in range(52):
            self.colour_tracks[1*57 + i] = cython.cast(cython.short, i + 18)
        for i in range(6):
            self.colour_tracks[1*57 + i + 51] = cython.cast(cython.short, i + 69)


        # GREEN
        for i in range(4):
            self.colour_bases[2*4 + i] = cython.cast(cython.short, i + 5)
        for i in range(52):
            self.colour_tracks[2*57 + i] = cython.cast(cython.short, i + 31) if i + 31 <= 68 else cython.cast(cython.short, i - 21)
        for i in range(6):
                self.colour_tracks[2*57 + i + 51] = cython.cast(cython.short, i + 75)

        # YELLOW
        for i in range(4):
            self.colour_bases[3*4 + i] = cython.cast(cython.short, i + 9)
        for i in range(52):
            self.colour_tracks[3*57 + i] = cython.cast(cython.short, i + 44) if i + 44 <= 68 else cython.cast(cython.short, i - 8)
        for i in range(6):
            self.colour_tracks[3*57 + i + 51] = cython.cast(cython.short, i + 81)

        # BLUE
        for i in range(4):
            self.colour_bases[4*4 + i] = cython.cast(cython.short, i + 13)
        for i in range(52):
            self.colour_tracks[4*57 + i] = cython.cast(cython.short, i + 57) if i + 57 <= 68 else cython.cast(cython.short, i + 5)
        for i in range(6):
            self.colour_tracks[4*57 + i + 51] = cython.cast(cython.short, i + 87)

        for i in range(93):
            self.stars[i] = 1 if i in [18, 26, 31, 39, 44, 52, 57, 65] else 0
            self.final_pos[i] = 1 if i in [74, 80, 86, 92] else 0

    def __dealloc__(self):
        free(self.stars)
        free(self.final_pos)
        free(self.colour_bases)
        free(self.colour_tracks)


@cython.cclass
class Block:
    pawns: cython.short
    pos: cython.short
    rigid: cython.bint

    def __init__(self, pawns, pos, rigid):
        self.pawns = pawns
        self.pos = pos
        self.rigid = rigid


@cython.cclass
class State:
    game_over: cython.bint
    current_player: cython.short
    num_more_moves: cython.short
    dice_roll: cython.short
    last_move_id: cython.short
    colour_pos: cython.p_short
    all_block: list[Block]

    def __init__(self):
        self.colour_pos = cython.cast(cython.p_short, calloc(5*93, cython.sizeof(cython.short)))
        self.blocks = []

    def __decalloc__(self):
        free(self.colour_pos)

