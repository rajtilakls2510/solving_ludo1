from cython.cimports.ludoc import *
from cython.cimports.openmp import omp_lock_t

cdef struct MCTSNode:
    StateStruct state
    MCTSNode* parent
    AllPossibleMovesReturn all_moves
    bint expanded
    omp_lock_t access_lock
    MCTSNode* children
    short move_start
    short move_end
    int* p
    int* n
    int* w
    int* q

