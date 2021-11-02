from setuptools import setup
from setuptools import find_packages

setup(
    name="svoe_featurizer",
    version="0.0.1",
    author="Andrey Novitskiy",
    author_email="valera.dirty@gmail.com",
    description=("Real-time/offline feature calculation for SVOE"),
    url="https://github.com/dirtyValera/svoe",
    packages=find_packages(),
    install_requires=[
        "pyzmq",
    ],
    entry_points={
        'console_scripts': ['svoe_featurizer_launch=featurizer.bin.launcher:main'],
    }
)