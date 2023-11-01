# Featurizer Storage and Data Models

## Overview

Featurizer stores contents of features and data sources in blocks of timestamp-sorted records. For range-based queries and 
other parametrized data access it keeps an index of all the blocks metadata (i.e. start and end timestamps, in-memory and 
on-disk size, user-defined parameters, etc.) in a SQL database (currently supports MySQL or SQLite). Each block is represented 
as a pandas DataFrame when loaded in memory or as a gzip-compressed parquet file when stored on disk or blob storage.

## Data Models

There are 4 main user-facing data models

- **Block**

Single block of data, currently a simple pandas dataframe
```
Block = pd.DataFrame
``` 

- **BlockRange**

Represents a range of consecutive timestamp-sorted blocks. These are treated as a single range that contains no gaps. 
Blocks are considered consecutive if time difference between them is no more than user-defined delta.
```
BlockRange = List[Block]
```

- **BlockMeta**
Represents block metadata: feature/data source name, key or id, time range, size, etc.
```
BlockMeta = Dict
```


- **BlockRangeMeta**
Similarly to *BlockRange*, represents metadata for consecutive blocks.
```
BlockRangeMeta = List[BlockMeta]
```

## SQL Tables

Metadata about features/data sources and feature/data source blocks is stored in 4 tables

- ```features_metadata```
- ```data_sources_metadata```
- ```feature_blocks_metadata```
- ```data_source_blocks_metadata```


## Data Store Adapters

Featurizer provides ```DataStoreAdapter``` class to implement custom read/write operations for block storage.
Users are able to extend this class with their own logic.

```
class DataStoreAdapter:

    def load_df(self, path: str, **kwargs) -> pd.DataFrame:
        raise NotImplementedError

    def store_df(self, path: str, df: pd.DataFrame, **kwargs):
        raise NotImplementedError

    def make_feature_block_path(self, item: FeatureBlockMetadata) -> str:
        raise NotImplementedError

    def make_data_source_block_path(self, item: DataSourceBlockMetadata) -> str:
        raise NotImplementedError
```


Featurizer includes implementation two data store adapters:

- ```LocalDataStoreAdapter```
Stores and reads data from local filesystem
- ```RemoteDataStoreAdapter```
Stores and reads data from S3

By default, ```LocalDataStoreAdapter``` is used


## Data Access API

# TODO implement data access api
