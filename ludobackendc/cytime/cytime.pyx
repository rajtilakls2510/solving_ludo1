cdef extern from "timemodule.c" nogil:
    double floattime()
    int floatsleep(double secs)

cdef double time() noexcept nogil:
    return floattime()

cdef int sleep(double secs) noexcept nogil:
    return floatsleep(secs)
