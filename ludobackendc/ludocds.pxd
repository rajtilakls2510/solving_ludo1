
cdef struct AllMovesTreeNode:
    int pawn
    short current_pos
    short destination
    AllMovesTreeNode * next
    AllMovesTreeNode * child