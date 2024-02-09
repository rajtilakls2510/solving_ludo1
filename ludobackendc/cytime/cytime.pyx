cdef extern from "timemodule.c" nogil:
    int floatsleep(double secs)

cdef int sleep(double secs) noexcept nogil:
    return floatsleep(secs)
