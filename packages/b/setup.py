from setuptools import setup, Extension

setup(
    ext_modules=[
        Extension("b._native", sources=["b/_native.c"]),
    ],
)
