# About SVOE

SVOE is not about code, models or formulas. It's about dream, vision and connecting like-minded people together.
Currently, we have completed an alpha DevOps setup and have one fully operational service - data_feed

# data_feed service

Data Feed Service is responsible for subscribing to configured exchanges/channels/symbols, processing raw data into
common formats (unathenticated channels only for us - tickers, l2/l3 books, trade updates, etc.) and pusing it down
to subscribers (we aim to use ZMQ sockets for IPC/pod-to-pod communication) as well as storing small blocks of
aggregated data to remote store (currently Amazon S3 + Amazon Glue DB to be used with Amazon Athena).

Essentially, it is a wrapper around [cryptostore fork](https://github.com/dirtyValera/cryptostore), which is in turn a service utilizing [cryptofeed](https://github.com/dirtyValera/cryptofeed), entrypoint in `svoe/data_feed/data_feed/data_feed_service.py`

### About cryptofeed

Shortly, it contains `Feed` and `FeedHandler` objects, which encapsulate exchange specific connection handling
(https retries/rate limits, websocket reconnects etc.) as well as parsing messages to common data formats and pushing it
down to custom callbacks (Redis/ZMQ etc.)
It utilizes Cython at latency critical paths (e.g. orderbook construction). It also provides a flexible configuration.

Our fork also enables exporting Prometheus metrics

### About cryptostore

Cryptostore is a python multiprocess app, utilizing cryptofeed to be executed as a contanirized application.

Key processes:

* `Cryptostore` (`cryptostore/cryptostore/cryptostore.py`) - main process to launch an app, parse config, do one-time pre-lauch
operations and launch other processes (namely `Spawner` and `Aggregator`)
* `Spawner` (`cryptostore/cryptostore/spawn.py`) - process to launch `Collector` processes depending on current config
* `Collector` (`cryptostore/cryptostore/collector.py`) - process to launch/handle cryptofeed's `FeedHandler` objects as
configured by user. We configure those to write data to Redis as a temporary cache. App is configured to launch one `Collector` per exchange.
(`cryptofeed/cryptofeed/backends/redis.py`).
* `Aggregator` (`cryptostore/cryptostore/aggregator/aggregator.py`, this file contains some irrelevant to us logic) -
process to periodically aggregate data from cache (Redis in our case) and write it to remote store (s3 + Glue Db).
In our case write logic is in `SvoeStore` object.
* `SvoeStore` (`cryptostore/cryptostore/data/svoe_store.py`) - logic to write aggregated data to remote store. It uses
Python's [awsdatawrangler](https://aws-data-wrangler.readthedocs.io/en/stable/) package to simply write Pandas dataframe object to s3 file and simultaneously update
corresponding Glue DB schema


To view configuration, check out `svoe/data_feed/data-feed-config.yaml` for out fork-specific config or
`cryptostore/cryptostore/config.yaml` for upstream version.

Fork specific features:

* Custom config (`svoe/data_feed/data-feed-config.yaml`)
* Prometheus multiproc exporter (`cryptostore/cryptostore/metrics.py`)
* Health check endpoint (`cryptostore/cryptostore/health.py`)
* Writing config to Mysql on start (`cryptostore/cryptostore/sql/models.py`)
* `SvoeStore` remote store connector (`cryptostore/cryptostore/data/svoe_store.py`)

During development, we try to move away from using 'cryptostore' terminology outside of cryptostore library,
e.g. instead of having `cryptostore-config.yaml` we have `data-feed-config.yaml`. In future, cryptstore dependency is
planned to be deprecated by moving all necessary functionality directly to data_feed directory while leaving parts
which are not used by us (Kafka cache, different types of remote store connectors, plugin controllers, etc.)


### Running with docker-compose

* Make sure docker is installed (we use Docker for Mac desktop app)
* Clone [cryptofeed](https://github.com/dirtyValera/cryptofeed) fork
* Clone [cryptostore](https://github.com/dirtyValera/cryptostore) fork
* Clone [svoe](https://github.com/dirtyValera/svoe)
* Make sure all 3 folders are in the same directory, not inside each other
* `cd svoe/data_feed`
* Default dev setup for docker-compose is in `docker-compose.yaml`. Before launching `sudo docker-compose up` make sure we have all necessary env vars set up
   * `ENV=DEV` (this is already in `docker-compose.yaml`)
   * Create file `svoe/data_feed/secrets_DO_NOT_COMMIT.env` with sensitive data (see example in `svoe/data_feed/secrets_EXAMPLE.env`).
   This file should be in `.gitignore`
* `sudo docker-compose up`. This will use default `docker-compose.yaml` which uses `Dockerfile-dev` for `svoe_data_feed` service as well as a
   number of dependant services (see `docker-compose.yaml`). Most of this services expose ports and can be
   accessed via localhost (e.g. to view Grafana dashboards or run a Prometheus query):
   * Redis (see External dependencies)
   * Mysql (see External dependencies)
   * dumper-restorer (see External dependencies)
   * Prometheus (for local dev see svoe_data_feed/common/services/prometheus)
   * Grafana (for local dev see svoe_data_feed/common/services/grafana)
   * Alertmanager (for local dev see svoe_data_feed/common/services/alertmanager)
   * AlertmanagerTelegramBot (for local dev see svoe_data_feed/common/services/alertmanager_telegram_bot)
* For dev environment, `docker-compose.yaml` mounts `cryptofeed` and `cryptostore` folders to `svoe_data_feed` container and
   `Dockerfile-dev` makes sure mounted paths are added to `PYTHONPATH` envvar inside the container. This helps us instantly pick up
   changes in those directories outside the container without rebuilding the image on each code change. The only time we need to rebuild
   the image is when adding extra pip packages to `data_feed` package.
* To launch prod image use `sudo docker-compose -f docker-compose.yaml -f docker-compose.prod.yaml up`.
   This will use `docker-compose.prod.yaml` override which points to `Dockerfile` containing prod spec
* To launch resource monitoring services add `-f docker-compose.resource-monitoring.yaml` to `docker-compose`.
   This will launch two services described in `docker-compose.resource-monitoring.yaml` exporting resource related metrics to Prometheus:
   
   * [nodeexporter](https://github.com/prometheus/node_exporter)
   * [cAdvisor](https://github.com/google/cadvisor)
   
   After launch, these can be viewed in Grafana


### External dependencies

* Redis - used as a cache for data_feed. In prod setting, each data_feed pod has a small sidecar Redis container.
* Mysql - for now, used to store only data_feed configuration files on each start
* dumper-restorer - this container is necessary to sync Mysql data with s3 backup file on each start
(dumping on destroy is not configured now for Docker but works on Kubernetes cluster).
Scripts which are used for these are stored in `svoe/helm/charts/local/mysql-extra/scripts`


### Breaking external dependencies

By default, without changing certain `data-feed-config.yaml` values and certain env vars for `data_feed` as well as other services,
`data_feed` will not be fully operational and will throw exceptions. These include:

* dumper_restorer + Mysql dependency - by default, data_feed container tries to connect to Mysql container and
  write config. If connection is not established or if the DB configured via `MYSQL_DATABASE` env var is not present in Mysql,
  exception will be thrown and container will crash. dumper_restorer container is responsible for creating
  `MYSQL_DATABASE` db from s3 backup file (or from scratch if not present), however if it is not able to read
  s3 mysql backup bucket configured via `AWS_S3_MYSQL_BUCKET` env var it will retry forever, resulting in `svoe_data_feed` container
  crashing indefinitely. Since `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are not configured by default either
  (or have no permissions to access certain bucket), this won't work. Some options to bypass this:

   * Comment out code to write config to mysql (`_save_config_mysql` in `cryptostore/cryptostore/cryptostore.py`)
   * Configure your own s3 backup bucket and add permissions to your AWS keys (preferably via terraform). This will have to
    be discussed as a broader conversation of multidev setup (now all we have is for one-man team)
   * Use existing backup bucket by asking admin/owner to give you keys with appropriate permissions (again, need to think how
    one-bucket-for-all-devs approach would work)

* S3 + Glue dependency - Similarly to above, `data_feed` uses `SvoeStore` from `cryptostore` to write data to pre-configured
  s3 bucket + Glue DB. Those are described in terraform (`svoe/terraform/modules/aws/glue` module). Also note that
  s3 bucket used to store all `data_feed` remote data (referred as 'data_lake') 'svoe.test.1' is not configured in terraform
  and only referenced by name (this should be improved). Developer will also need `AWS_ACCESS_KEY_ID` and
  `AWS_SECRET_ACCESS_KEY` with appropriate permissions from admin if using existing s3 bucket+Glue DB. Some options to bypass this:

   * Comment out relevant code in `SvoeStore`
   * Create your own AWS infra via terraform (`terraform plan -target=module.aws.glue`). This will require setting up
   AWS account as well as manually creating data_lake bucket (better update existing terraform code to do it automatically).
   * Use existing AWS infra, get keys with permissions from admin. For now, the existing bucket is used for both prod and dev writing. This should be improved.
   * All of the above should start a conversation about setting up multi-dev AWS infra.



### Running locally

If you want to be able to attach Python debugger to running processes you need to be able to run `data_feed` locally. This
should require doing steps described in `svoe/data_feed/Dockerfile-dev`. You will also need to make sure all service dependencies are ok locally.

* Install python v3+
* pull projects described above
* Update `PYTHONPATH` env var (see Dockerfile-dev) (use `sys.path.append` ?)
* Set up necessary env vars (see `docker-compose.yaml`)
* pip dependencies are specified in `svoe/data_feed/requirements-dev.txt` (you can run `pip install -r requirements-dev.txt`)
* note that `cryptofeed` uses `Cython` which may require running `setuptools` by running `python setup.py install` inside cryptofeed dir.
In docker, this step is done inside service itself via running `pyximport.install()` in the beggining of imports in `svoe/data_feed/data_feed/data_feed_service.py`.
If you have `ENV=DEV` env var set locally, this may work okay (not sure)
* Some dependencies may still be missing and require manual installation (`setup.py` files in forks of `cryptostore`
and `cryptofeed` are changed to remove `install_requires` values for reasons I do not fully remember now,
mainly to work well with Docker for both dev and prod environments). This can be improved.
* Note that `svoe/data_feed/data_feed/data_feed_service.py` uses hardcoded path to config (
`DATA_FEED_CONFIG_PATH = '/etc/svoe/data_feed/configs/data-feed-config.yaml'`), so `svoe/data_feed/data-feed-config.yaml` should be copied there
* Check out `svoe/test.py` to see how to import `data_feed` package and launch it (simply run `python3 svoe/test.py`)

### Future work
* TODO


# Other parts of the project (TODO more details)

# DevOps

This part has taken most of the dev capacity so far and is considered to be operational.

### Terraform modules
* vpc-mesh
* kops stuff (s3 bucket, route 53 zones, generated configs)
* data_lake resources (s3 bucket + Glue DB for Athena)
* Elastic Container Regisrty (ECR)

### Kops utils
* multicluster template
* multicluster create/delete/upgrade scripts
* Cilium clustermesh setup and global services
* Syncing with Terraform

### Monitoring
* Thanos multicluser setup with Cilium clustermesh and S3 remote metric store

### Helmfile
* local and remote charts and templating
* local and remote values and templating
* helmfile apply/sync/diff/template on multicluster

### CI
* single script to update latest svoe_data_feed_prod image to ECR
* specifying data_feed image version in Helm

# Data ENG

This should contain all data transformation/ETL related workflows

* Scripts to read/write data from s3/Athena
* Common scripts (l2_book deltas to full, full to deltas, etc.)
* Pandas routines
* Fargate Spot cluster setup
* Running Dask on Farget Spot
* Running Prefect pipelines on Dask

# Other custom services

For now, data_feed is the only fully operational service with e2e dev setup, but we have started developing other stuff

### Featurizer

Service to subscribe to data_feed (potentially other services) via ZMQ sockets, calculate configured features and push
them down to subscribers (ZMQ as well)
* Currently has a rough skeleton and Dockerfile (svoe/featurizer)
* Plan is to use it in conjunction with [Feast](https://github.com/feast-dev/feast) Feature Store


# Deprecated stuff
* configs folder
* kubeflow folder
* data_feed/health_check (exposed as part of a service now)

# Next steps and planned work
* TODO


