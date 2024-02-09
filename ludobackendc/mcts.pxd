from cython.cimports.ludoc import *
from cython.cimports.openmp import omp_lock_t

cdef struct MCTSNode:
    StateStruct state
    MCTSNode* parent
    short* roll_num_moves
    MoveStruct* all_moves
    bint expanded
    omp_lock_t access_lock
    MCTSNode** children
    short move_start
    short move_end
    double* p
    int* n
    int* w
    double* q

