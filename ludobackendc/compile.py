import sys, os

sys.argv = ["compile.py", "build_ext", "--inplace"]

from distutils.core import setup, Extension
from Cython.Build import cythonize
import glob

for ff in ("*.c", "*.html"):
    for f in glob.glob(ff):
        try:
            os.remove(f)
        except FileNotFoundError:
            pass

ext_modules = [
    Extension("ludoc", ["ludoc.py"], extra_compile_args=["-fopenmp"], extra_link_args=[]) # /openmp
]

setup(name="ludo", ext_modules=cythonize(ext_modules, annotate=True, compiler_directives={"language_level": "3"}))
