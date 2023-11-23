# Data Ingest Pipeline

To get input data into SVOE, Featurizer provides two main methods: **[Data Ingest Pipeline](https://anovv.github.io/svoe/featurizer-data-ingest/)** and **[Real Time Data Recording](https://anovv.github.io/svoe/featurizer-real-time-data-recording/)**.
This section will describe the former.

Featurizer provides a scalable, configurable and extensible data ingest pipeline
which takes (offline) raw user data and puts it in Featurizer storage. It takes care of such
things as indexing, compaction, per-data type resource allocation for pipeline workers and many other data
engineering related problems. It integrates with DataSourceDefinition class so users
can easily add their own processing logic in a modular way without spinning up and maintaining
data engineering infrastructure.

## Usage

* CLI: ```svoe featurizer run-data-ingest <path_to_config>```
* API: ```FeaturizerDataIngestPipelineRunner.run(path_to_config)```

## Config
 
TODO describe options

```
provider_name: cryptotick
batch_size: 12
max_executing_tasks: 10
data_source_files:
  - data_source_definition: featurizer.data_definitions.common.l2_book_incremental.cryptotick.cryptotick_l2_book_incremental.CryptotickL2BookIncrementalData
    files_and_sizes:
      - ['limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz', 252000]
      - ['limitbook_full/20230202/BINANCE_SPOT_BTC_USDT.csv.gz', 252000]
      - ['limitbook_full/20230203/BINANCE_SPOT_BTC_USDT.csv.gz', 252000]
      - ['limitbook_full/20230204/BINANCE_SPOT_BTC_USDT.csv.gz', 252000]
```