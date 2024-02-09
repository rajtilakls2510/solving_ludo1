"""
Cdef wrappings of functions from Python's time module.

This allows one to call time-related functions from Cython retaining
the platform-independence one is used to from Python.
"""

# NOTE: Unlike time's sleep, this DOES NOT release the GIL.
cdef int sleep(double secs) noexcept nogil

