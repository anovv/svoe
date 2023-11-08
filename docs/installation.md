Install from PyPi. Be aware that Svoe requires Python 3.10+.

```
pip install svoe
```

For local environment launch standalone setup on your laptop. This will start local Ray cluster, create and populate 
SQLite database, spin up MLFlow tracking server and load sample data from remote store (S3). Make sure you have
all necessary dependencies present
```
svoe standalone
```

For distributed setting, please refer to [Running on remote clusters](TODO)

