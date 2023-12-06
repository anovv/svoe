from setuptools import setup
from setuptools import find_packages

setup(
    name="svoe_configs",
    version="0.0.1",
    author="Andrey Novitskiy",
    author_email="valera.dirty@gmail.com",
    description=("Configurations generation for SVOE"),
    url="https://github.com/dirtyValera/svoe",
    packages=find_packages(),
    install_requires=[
        "cryptostore @ git+https://github.com/dirtyValera/cryptostore.git",
    ],
    entry_points={
        'console_scripts': ['svoe_data_feed_launch=data_feed.bin.launcher:main'],
    }
)