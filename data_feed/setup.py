from setuptools import setup
from setuptools import find_packages

setup(
    name="data_feed",
    version="0.0.1",
    author="Andrey Novitskiy",
    author_email="valera.dirty@gmail.com",
    description=("Data feed for SVOE"),
    url="https://github.com/dirtyValera/svoe",
    packages=find_packages(),
    install_requires=[
        "cryptostore",
        "boto3",
        "aiokafka",
        "confluent-kafka",
    ],
    entry_points={
        'console_scripts': ['svoe_data_feed_launch=data_feed.bin.launcher:main'],
    }
)