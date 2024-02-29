import sys, os

sys.argv = ["compile.py", "build_ext", "--inplace"]

from distutils.core import setup, Extension
from Cython.Build import cythonize
import glob

for ff in ("*.c", "*.html", "*.pyd", "*.so"):
    for f in glob.glob(ff):
        try:
            os.remove(f)
        except FileNotFoundError:
            pass

if sys.platform.startswith("win"):
    openmp_arg = '/openmp'
else:
    openmp_arg = '-fopenmp'

ext_modules = [
    Extension("cytime", ["cytime/*.pyx", "cytime/timemodule.c"]),
    Extension("ludoc", ["ludoc.py"], extra_compile_args=[openmp_arg], extra_link_args=[openmp_arg]),
    Extension("mcts", ["mcts.py"], extra_compile_args=[openmp_arg], extra_link_args=[openmp_arg]),
    Extension("cysimdjson.cysimdjson", ['cysimdjson/cysimdjson.pyx',
                                            'cysimdjson/simdjson/simdjson.cpp',
                                            'cysimdjson/pysimdjson/errors.cpp',
                                            'cysimdjson/cysimdjsonc.cpp', ],
                  language="c++",
                  extra_compile_args=[
                      "-std=c++17",  # for std::string_view class that became standard in C++17
                      "-Wno-deprecated",
                  ] if sys.platform != "win32" else [  # NOTE Windows doesn't know how to handle "-Wno-deprecated"
                      "/std:c++17",
                  ],
                  define_macros=[("CYTHON_EXTERN_C", 'extern "C"')]
                  )  # -fopenmp
]

setup(name="ludo", ext_modules=cythonize(ext_modules, annotate=True, compiler_directives={"language_level": "3"}))
