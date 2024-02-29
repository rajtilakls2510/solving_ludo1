
cdef struct AllMovesTreeNode:
    int pawn
    short current_pos
    short destination
    AllMovesTreeNode * next
    AllMovesTreeNode * child

cdef struct Block:
    int pawns
    short pos
    bint rigid

cdef struct StateStruct:
    short n_players
    bint game_over
    short current_player
    short num_more_moves
    short dice_roll
    short last_move_id
    int* pawn_pos
    short num_blocks
    Block[16] all_blocks

cdef struct MoveStruct:
    short n_rolls
    int* pawns
    short* current_positions
    short* destinations

cdef struct AllPossibleMovesReturn:
    short* roll_num_moves
    MoveStruct** roll_moves


cdef StateStruct generate_next_state1(StateStruct state, MoveStruct move, short* colour_tracks, short* stars, short* final_pos, short* player_colours) noexcept nogil

cdef AllPossibleMovesReturn all_possible_moves1(StateStruct state, short* stars, short* final_pos, short* colour_tracks, short* player_colours) noexcept nogil

cdef StateStruct copy_state(StateStruct) noexcept nogil

cdef short roll_sum_to_mod(short sum) noexcept nogil

cdef void free_state(StateStruct state) noexcept nogil

cdef void free_move(MoveStruct move) noexcept nogil

cdef void free_all_possible_moves_return(AllPossibleMovesReturn all_moves) noexcept nogil

cdef bint check_completed1(StateStruct state, short player, short* final_pos) noexcept nogil

cdef void get_tensor_repr_nogil(StateStruct state_struct, short n_players, short[5] colour_player, float[:,:] representation) noexcept nogil

cdef class State:
    cdef StateStruct state_struct
    cdef void set_structure(State s, StateStruct st)

cdef class GameConfig:
    cdef public:
        short n_players
    cdef short* player_colours
    cdef short[5] colour_player

cdef class LudoModel:
    cdef public:
        GameConfig config
    cdef short* stars
    cdef short* final_pos
    cdef short* colour_tracks
    cdef short* colour_bases