# cython: cdivision = True
import cython
from cython.cimports.libc.stdlib import free, calloc

Block = cython.struct(pawns=cython.int, pos=cython.short, rigid=cython.bint)

StateStruct = cython.struct(
    n_players=cython.short,
    game_over=cython.bint,
    current_player=cython.short,
    num_more_moves=cython.short,
    dice_roll=cython.short,
    last_move_id=cython.short,
    pawn_pos=cython.p_int,
    num_blocks=cython.short,
    all_blocks=Block[16]
)

MoveStruct = cython.struct(n_rolls=cython.short, pawns=cython.p_int, current_positions=cython.p_short, destinations=cython.p_short)

NextStateReturn = cython.struct(next_state=StateStruct, num_more_moves=cython.short)
NextPossiblePawnReturn = cython.struct(pawns=cython.p_int, current_pos=cython.p_short, n=cython.short)
ValidateMoveReturn = cython.struct(valid=cython.bint, destination=cython.short)


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def copy_state(state: StateStruct) -> StateStruct:
    new_state: StateStruct = state
    pawn_pos: cython.p_int = cython.cast(cython.p_int, calloc(state.n_players * 93, cython.sizeof(cython.int)))
    i: cython.Py_ssize_t
    for i in range(state.n_players * 93):
        pawn_pos[i] = state.pawn_pos[i]
    new_state.pawn_pos = pawn_pos
    return new_state


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def copy_move(move: MoveStruct) -> MoveStruct:
    pawns: cython.p_int = cython.cast(cython.p_int, calloc(move.n_rolls, cython.sizeof(cython.int)))
    current_positions: cython.p_short = cython.cast(cython.p_short, calloc(move.n_rolls, cython.sizeof(cython.short)))
    destinations: cython.p_short = cython.cast(cython.p_short, calloc(move.n_rolls, cython.sizeof(cython.short)))
    i: cython.short
    for i in range(move.n_rolls):
        pawns[i] = move.pawns[i]
        current_positions[i] = move.current_positions[i]
        destinations[i] = move.destinations[i]
    move.pawns = pawns
    move.current_positions = current_positions
    move.destinations = destinations
    return move


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def move_single_pawn(state: StateStruct, pawn: cython.int, current_pos: cython.short,
                     destination: cython.short) -> cython.void:
    new_pawns: cython.int = 0
    p: cython.int = state.pawn_pos[state.current_player * 93 + current_pos]
    while p != 0:
        if (p % 17) != pawn:
            new_pawns = new_pawns * 17 + (p % 17)
        p //= 17
    state.pawn_pos[state.current_player * 93 + current_pos] = new_pawns
    state.pawn_pos[state.current_player * 93 + destination] = state.pawn_pos[
                                                                  state.current_player * 93 + destination] * 17 + pawn


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def find_pawn_in_agg(pawns: cython.int, pawn: cython.int) -> cython.bint:
    while pawns != 0:
        if pawns % 17 == pawn:
            return True
        pawns //= 17
    return False


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def check_pawns_same(pawns1: cython.int, pawns2: cython.int) -> cython.bint:
    p1: cython.int = pawns1
    while p1 != 0:
        if not find_pawn_in_agg(pawns2, p1 % 17):
            return False
        p1 //= 17
    return True


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def replace_pawn_in_aggregate(pawns: cython.int, pawn_to_replace: cython.int,
                              pawn_to_be_replaced_with: cython.int) -> cython.int:
    p1: cython.int = 0
    while pawns != 0:
        if (pawns % 17) == pawn_to_replace:
            pawns = (pawns // 17) * 17 + pawn_to_be_replaced_with
            break
        else:
            p1 = p1 * 17 + pawns % 17
        pawns //= 17
    while p1 != 0:
        pawns = pawns * 17 + p1 % 17
        p1 //= 17
    return pawns


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def add_block(state: StateStruct, pawns: cython.int, pos: cython.short, rigid: cython.bint) -> StateStruct:
    state.all_blocks[state.num_blocks] = Block(pawns=pawns, pos=pos, rigid=rigid)
    state.num_blocks += 1
    return state


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def remove_block(state: StateStruct, index: cython.Py_ssize_t) -> StateStruct:
    state.num_blocks -= 1
    state.all_blocks[index] = state.all_blocks[state.num_blocks]
    return state


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def find_next_possible_pawns(state: StateStruct, stars: cython.p_short,
                             final_pos: cython.p_short) -> NextPossiblePawnReturn:
    # Collect all next possible pawns
    current_player: cython.short = state.current_player
    next_possible_pawns: cython.p_int = cython.cast(cython.p_int, calloc(93 + 16, cython.sizeof(cython.int)))
    current_pos: cython.p_short = cython.cast(cython.p_short, calloc(93 + 16, cython.sizeof(cython.short)))
    num: cython.short = 0

    # Single pawn forward
    i: cython.short
    for i in range(93):
        if final_pos[i] == 0:
            p: cython.int = state.pawn_pos[current_player * 93 + i]
            while p != 0:
                j: cython.short
                for j in range(state.num_blocks):
                    if state.all_blocks[j].pos == i and not find_pawn_in_agg(state.all_blocks[j].pawns, p % 17):
                        next_possible_pawns[num] = p % 17
                        current_pos[num] = i
                        num += 1
                        break
                p //= 17

    # Single pawn forward with block
    i: cython.short
    for i in range(93):
        p1: cython.int = state.pawn_pos[current_player * 93 + i]
        while p1 > 16:
            p2: cython.int = p1 // 17
            while p2 != 0:
                p1_addable: cython.bint = True
                p2_addable: cython.bint = True
                j: cython.short
                for j in range(state.num_blocks):
                    if state.all_blocks[j].pos == i:
                        p1_addable = p1_addable and not find_pawn_in_agg(state.all_blocks[j].pawns, p1 % 17)
                        p2_addable = p2_addable and (
                                    not find_pawn_in_agg(state.all_blocks[j].pawns, p2 % 17) or not state.all_blocks[
                                j].rigid)
                if p1_addable and p2_addable:
                    next_possible_pawns[num] = (p1 % 17) * 17 + p2 % 17
                    current_pos[num] = i
                    num += 1
                p2 //= 17
            p1 //= 17

    # Block pawn forward
    j: cython.short
    for j in range(state.num_blocks):
        if find_pawn_in_agg(state.pawn_pos[current_player * 93 + state.all_blocks[j].pos],
                            state.all_blocks[j].pawns % 17):
            next_possible_pawns[num] = state.all_blocks[j].pawns
            current_pos[num] = state.all_blocks[j].pos
            num += 1

    # Block pawn forward unblocked after star or unrigid block
    j: cython.short
    for j in range(state.num_blocks):
        if (stars[state.all_blocks[j].pos] > 0 or not state.all_blocks[j].rigid) and find_pawn_in_agg(
                state.pawn_pos[current_player * 93 + state.all_blocks[j].pos],
                state.all_blocks[j].pawns % 17):
            p: cython.int = state.all_blocks[j].pawns
            while p != 0:
                next_possible_pawns[num] = p % 17
                current_pos[num] = state.all_blocks[j].pos
                num += 1
                p //= 17

    return NextPossiblePawnReturn(pawns=next_possible_pawns, current_pos=current_pos, n=num)


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def validate_pawn_move(state: StateStruct, roll: cython.short, current_pos: cython.short, pawn: cython.int, stars: cython.p_short, final_pos: cython.p_short, colour_tracks: cython.p_short) -> ValidateMoveReturn:
    # Calculate whether the move is valid given the state configuration and return the new positions of the pawns
    current_player: cython.short = state.current_player

    # TO VERIFY:
    # Single pawns:
    if pawn <= 16:
        colour: cython.short = (pawn - 1) // 4 + 1
        # Pawns only go to it's track only on 6 roll.
        if current_pos == pawn and roll != 6:
            return ValidateMoveReturn(valid=False, destination=0)
        if current_pos == pawn and roll == 6:
            return ValidateMoveReturn(valid=True, destination=colour_tracks[colour * 57 + 0])
        # Pawns cannot jump beyond its track
        i: cython.short
        index: cython.short = 0
        for i in range(57):
            if colour_tracks[colour * 57 + i] == current_pos:
                index = i
                if index + roll >= 57:
                    return ValidateMoveReturn(valid=False, destination=0)
        # Pawns cannot jump over other pawn blocks except pos is a base star
        i: cython.short
        for i in range(index + 1, index + roll):
            pos: cython.short = colour_tracks[colour * 57 + i]
            if stars[pos] < 2:
                player: cython.short
                for player in range(state.n_players):
                    if player != current_player and state.pawn_pos[player * 93 + pos] > 16:
                        return ValidateMoveReturn(valid=False, destination=0)
        # Pawns cannot move to a destination if the same player's one block and one single pawn is present except base star and final position
        destination: cython.short = colour_tracks[colour * 57 + index + roll]
        if stars[destination] < 2 and final_pos[destination] == 0:
            p: cython.int = state.pawn_pos[current_player * 93 + destination]
            i: cython.short = 0
            while p != 0:
                i += 1
                p //= 17
            if i >= 3:
                return ValidateMoveReturn(valid=False, destination=0)
    # Block Pawns:
    else:
        if roll % 2 != 0:
            return ValidateMoveReturn(valid=False, destination=0)
        # Block Pawns cannot jump beyond their track
        pawn1: cython.int = pawn % 17
        pawn1_colour: cython.short = (pawn1 - 1) // 4 + 1
        pawn2: cython.int = pawn // 17
        pawn2_colour: cython.short = (pawn2 - 1) // 4 + 1
        pawn1_index: cython.short = 0
        pawn2_index: cython.short = 0
        i: cython.short
        for i in range(57):
            if colour_tracks[pawn1_colour * 57 + i] == current_pos:
                pawn1_index = i
            if colour_tracks[pawn2_colour * 57 + i] == current_pos:
                pawn2_index = i
        if pawn1_index + roll // 2 >= 57 or pawn2_index + roll // 2 >= 57:
            return ValidateMoveReturn(valid=False, destination=0)
        # Move is possible only if both BlockPawns land at the same place after moving
        if colour_tracks[pawn1_colour * 57 + pawn1_index + roll // 2] != colour_tracks[pawn2_colour * 57 + pawn2_index + roll // 2]:
            return ValidateMoveReturn(valid=False, destination=0)
        # Block Pawns cannot jump over other pawn blocks except pos is a base star
        i: cython.short
        for i in range(pawn1_index + 1, pawn2_index + roll // 2):
            pos: cython.short = colour_tracks[pawn1_colour * 57 + i]
            if stars[pos] < 2:
                player: cython.short
                for player in range(state.n_players):
                    if player != current_player and state.pawn_pos[player * 93 + pos] > 16:
                        return ValidateMoveReturn(valid=False, destination=0)
        # Block Pawns cannot move to a destination if the same player's another block is present except final position
        destination = colour_tracks[pawn1_colour * 57 + pawn1_index + roll // 2]
        if final_pos[destination] == 0:
            if state.pawn_pos[current_player * 93 + destination] > 16:
                return ValidateMoveReturn(valid=False, destination=0)
    return ValidateMoveReturn(valid=True, destination=destination)


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def generate_next_state_inner(state: StateStruct, roll: cython.short, current_pos: cython.short, pawn: cython.int,
                              colour_tracks: cython.p_short, stars: cython.p_short,
                              final_pos: cython.p_short) -> NextStateReturn:
    state: StateStruct = copy_state(state)
    num_more_moves: cython.short = 0
    current_player: cython.short = state.current_player
    # If single pawn, find next position and update it
    if pawn <= 16:
        colour: cython.short = (pawn - 1) // 4 + 1
        index: cython.short = -6
        i: cython.short
        for i in range(57):
            if colour_tracks[colour * 57 + i] == current_pos:
                index = i
        destination: cython.short = colour_tracks[colour * 57 + index + roll]

        move_single_pawn(state, pawn, current_pos, destination)

        # If pawn is in a block, dissolve the block, leave the other pawn in old position
        i: cython.Py_ssize_t
        for i in range(state.num_blocks):
            block: Block = state.all_blocks[i]
            if find_pawn_in_agg(block.pawns, pawn):
                state = remove_block(state, i)
                break

        # If at current position two pawns are present and current position is not base star, block them up (non-rigid)
        if state.pawn_pos[state.current_player * 93 + current_pos] > 16 and stars[current_pos] != 2:
            new_pawns: cython.int = 0
            p: cython.int = state.pawn_pos[state.current_player * 93 + current_pos]
            i = 0
            while i < 2:
                new_pawns = new_pawns * 17 + (p % 17)
                p //= 17
                i += 1
            state = add_block(state, new_pawns, current_pos, False)

        # If another single pawn of other player is present at destination position (except stars), capture it by sending it back to its base
        if stars[destination] == 0:
            player: cython.short
            for player in range(state.n_players):
                if player != current_player:
                    pawn_to_capture: cython.int = 0
                    p: cython.int = state.pawn_pos[player * 93 + destination]
                    i: cython.Py_ssize_t
                    while p != 0:
                        for i in range(state.num_blocks):
                            if state.all_blocks[i].pos == destination:
                                if not find_pawn_in_agg(state.all_blocks[i].pawns, p % 17):
                                    pawn_to_capture = p % 17
                                    break
                        p //= 17
                    if pawn_to_capture != 0:
                        move_single_pawn(state, pawn_to_capture, destination,
                                         cython.cast(cython.short, pawn_to_capture))
                        num_more_moves += 1
                        break

        # If another single pawn of same player is present at destination position, block it with other pawn by default except the base star positions and finale position
        if stars[destination] < 2 and final_pos[destination] == 0 and state.pawn_pos[
            current_player * 93 + destination] > 16:
            state = add_block(state, state.pawn_pos[current_player * 93 + destination], destination, False)

        # If destination is finale and not all other pawns in finale position, give another move
        if final_pos[destination] == 1:
            i: cython.short
            for i in range(93):
                if i != destination and state.pawn_pos[current_player * 93 + destination] > 0:
                    num_more_moves += 1
                    break
    else:
        colour: cython.short = (pawn % 17 - 1) // 4 + 1
        index: cython.short = -6
        i: cython.short
        for i in range(57):
            if colour_tracks[colour * 57 + i] == current_pos:
                index = i
                break
        destination: cython.short = colour_tracks[colour * 57 + index + roll // 2]

        # If moving out of a base star, check whether the block is present or not. Make a block if not present.
        block_index: cython.short
        if stars[current_pos] == 2:
            state = add_block(state, pawn, current_pos, False)
            block_index = state.num_blocks - 1
        else:
            block_index = -1
            i: cython.short
            for i in range(state.num_blocks):
                if check_pawns_same(state.all_blocks[i].pawns, pawn):
                    block_index = i
                    break
            if block_index == -1:
                pawn_to_replace: cython.int = 0
                pawn_to_be_kept: cython.int = 0
                p: cython.int = pawn
                while p != 0:
                    for i in range(state.num_blocks):
                        if find_pawn_in_agg(state.all_blocks[i].pawns, p % 17):
                            block_index = i
                            pawn_to_be_kept = p % 17
                            break
                    else:
                        pawn_to_replace = p % 17
                        break
                    p //= 17
                pawn_to_be_replaced_with: cython.int
                p = state.all_blocks[block_index].pawns
                while p != 0:
                    if p % 17 != pawn_to_be_kept:
                        pawn_to_be_replaced_with = p % 17
                        break
                    p //= 17
                state.all_blocks[block_index].pawns = replace_pawn_in_aggregate(state.all_blocks[block_index].pawns,
                                                                                pawn_to_replace,
                                                                                pawn_to_be_replaced_with)

        state.all_blocks[block_index].pos = destination
        p: cython.int = state.all_blocks[block_index].pawns
        while p != 0:
            move_single_pawn(state, p % 17, current_pos, destination)
            p //= 17

        # If another Block pawn of other player is present at destination position (except stars), capture them by breaking the block and sending them back to their respective bases
        if stars[destination] == 0:
            player: cython.short
            for player in range(state.n_players):
                if player != state.current_player and state.pawn_pos[player * 93 + destination] > 16:
                    i: cython.short
                    for i in range(state.num_blocks):
                        if state.all_blocks[i].pos == destination and find_pawn_in_agg(
                                state.pawn_pos[player * 93 + destination], state.all_blocks[i].pawns % 17):
                            p: cython.int = state.all_blocks[i].pawns
                            state = remove_block(state, i)
                            while p != 0:
                                move_single_pawn(state, p % 17, destination, cython.cast(cython.short, p % 17))
                                p //= 17
                            num_more_moves += 2
                            break

        # If destination is base or finale position, break the block into single pawns
        if stars[destination] == 2 or final_pos[destination] == 1:
            state = remove_block(state, block_index)
        # Elif destination is an intermediate star, make the block not rigid
        elif stars[destination] == 1:
            state.all_blocks[block_index].rigid = False
        # Else, make the block rigid
        else:
            state.all_blocks[block_index].rigid = True

        # If destination is finale and not all other pawns in finale position, give two more moves
        if final_pos[destination] == 1:
            i: cython.short
            for i in range(93):
                if i != destination and state.pawn_pos[current_player * 93 + destination] > 0:
                    num_more_moves += 2
                    break

    return NextStateReturn(next_state=state, num_more_moves=num_more_moves)


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def check_block_no_moves_player(state: StateStruct, player: cython.short, player_colours: cython.p_short) -> cython.bint:
    # Checks whether a heterogeneous block is present at the top of the home stretch from which a player cannot take any move
    blocked: cython.short[5]
    blocked[0] = 0
    blocked[1] = 68
    blocked[2] = 29
    blocked[3] = 42
    blocked[4] = 55
    c: cython.short = player_colours[player]
    while c != 0:
        pos: cython.short = blocked[c % 5]
        i: cython.short
        for i in range(state.num_blocks):
            pawn_of_c_found: cython.bint = False
            pawn_diff_c_found: cython.bint = False
            p: cython.int = state.all_blocks[i].pawns
            while p != 0:
                pawn_of_c_found = pawn_of_c_found or ((p % 17 - 1) // 4 + 1 == c % 5)
                pawn_diff_c_found = pawn_diff_c_found or ((p % 17 - 1) // 4 + 1 != c % 5)
                p //= 17
            # If a block of the particular pawn is found, it is heterogeneous and rigid and in top of home stretch, then the player will have no moves
            if state.all_blocks[i].pos == pos and state.all_blocks[i].rigid and pawn_of_c_found and pawn_diff_c_found:
                return True
        c //= 5
    return False


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def check_available_moves(state: StateStruct, player: cython.short, final_pos: cython.p_short, player_colours: cython.p_short) -> cython.bint:
    if check_block_no_moves_player(state, player, player_colours):
        return False
    i: cython.short
    for i in range(93):
        if final_pos[i] != 1 and state.pawn_pos[player * 93 + i] > 0:
            return True
    return False


@cython.cfunc
@cython.nogil
@cython.exceptval(check=False)
def generate_next_state(state: StateStruct, move: MoveStruct, colour_tracks: cython.p_short, stars: cython.p_short, final_pos: cython.p_short, player_colours: cython.p_short) -> StateStruct:
    state: StateStruct = copy_state(state)
    if move.n_rolls > 0:
        total_moves: cython.short = state.num_more_moves
        i: cython.short
        r: cython.short = state.dice_roll
        for i in range(move.n_rolls):
            next_state_return: NextStateReturn = generate_next_state_inner(state, r % 7, move.current_positions[i], move.pawns[i], colour_tracks, stars, final_pos)
            state = next_state_return.next_state
            total_moves += next_state_return.num_more_moves
            r //= 7
        state.num_more_moves = total_moves
    # Update last move_id
    state.last_move_id += 1
    # Change the turn
    if state.num_more_moves == 0:
        state.current_player = (state.current_player + 1) % state.n_players
    # CHeck game over or not by evaluating if all other players have completed
    game_over: cython.bint = True
    player: cython.short
    for player in range(state.n_players):
        if player != state.current_player and check_available_moves(state, player, final_pos, player_colours):
            game_over = False
    state.game_over = game_over
    if state.num_more_moves > 0:
        state.num_more_moves -= 1
    return state


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
            self.stars[i] = 1 if i in [26, 39, 52, 65] else 0
            self.stars[i] = 2 if i in [18, 31, 44, 57] else 0
            self.final_pos[i] = 1 if i in [74, 80, 86, 92] else 0

    def __dealloc__(self):
        free(self.stars)
        free(self.final_pos)
        free(self.colour_bases)
        free(self.colour_tracks)


@cython.cfunc
def create_new_state(n_players: cython.short) -> StateStruct:
    pawn_pos: cython.p_int = cython.cast(cython.p_int, calloc(n_players * 93, cython.sizeof(cython.int)))
    state: StateStruct = StateStruct(n_players=n_players, game_over=False, current_player=0, num_more_moves=0,
                                     dice_roll=0, last_move_id=0, pawn_pos=pawn_pos, num_blocks=0)
    i: cython.Py_ssize_t
    for i in range(16):
        state.all_blocks[i] = Block(pawns=0, pos=cython.cast(cython.short, i), rigid=(i % 2 == 0))
    return state

@cython.cfunc
def create_new_move(n_rolls: cython.short) -> MoveStruct:
    pawns: cython.p_int = cython.cast(cython.p_int, calloc(n_rolls, cython.sizeof(cython.int)))
    current_positions: cython.p_short = cython.cast(cython.p_short, calloc(n_rolls, cython.sizeof(cython.short)))
    destinations: cython.p_short = cython.cast(cython.p_short, calloc(n_rolls, cython.sizeof(cython.short)))
    move: MoveStruct = MoveStruct(n_rolls=n_rolls, pawns=pawns, current_positions=current_positions, destinations=destinations)
    return move


@cython.cfunc
def free_state(state: StateStruct) -> cython.void:
    free(state.pawn_pos)

@cython.cfunc
def free_move(move: MoveStruct) -> cython.void:
    free(move.pawns)
    free(move.current_positions)
    free(move.destinations)
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

        pawn_pos = cython.cast(cython.p_int, calloc(state_dict['n_players'] * 93, cython.sizeof(cython.int)))
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
            pawns: cython.int = 0
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
                pawn: cython.int = s.pawn_pos[player * 93 + pos]
                while pawn != 0:
                    pawns.append(mappings["pawn"][pawn % 17])
                    pawn //= 17
                for p in pawns:
                    k[p] = mappings["pos"][pos]
        state["all_blocks"] = []
        i: cython.Py_ssize_t
        for i in range(s.num_blocks):
            pawns = []
            pawn: cython.int = s.all_blocks[i].pawns
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
