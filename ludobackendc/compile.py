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
    Extension("ludoc", ["ludoc.py"], extra_compile_args=[openmp_arg], extra_link_args=[openmp_arg]),
    Extension("mcts", ["mcts.py"], extra_compile_args=[openmp_arg], extra_link_args=[openmp_arg]),
    Extension("cytime", ["cytime/*.pyx", "cytime/timemodule.c"], extra_compile_args=["/openmp"], extra_link_args=["/openmp"]) # -fopenmp
]

setup(name="ludo", ext_modules=cythonize(ext_modules, annotate=True, compiler_directives={"language_level": "3"}))
