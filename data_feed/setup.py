from setuptools import setup
from setuptools import find_packages

setup(
    name="svoe_data_feed",
    version="0.0.1",
    author="Andrey Novitskiy",
    author_email="valera.dirty@gmail.com",
    description=("Data feed for SVOE"),
    url="https://github.com/dirtyValera/svoe",
    packages=find_packages(),
    # TODO figure out dependencies
    install_requires=[
    ],
    extras_require={
        'prod': ['cryptostore'], # TODO is this needed?
    },
    entry_points={
        'console_scripts': ['svoe_data_feed_launch=data_feed.bin.launcher:main'],
    }
)