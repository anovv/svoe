# DataSourceDefinition and Data Ingestion pipeline

## DataSourceDefinition overview

Similar to ```FeatureDefinition```, ```DataSourceDefinition``` defines a blueprint for a data source - a sequence 
of events which framework treats as an input to our feature calculation pipelines. ```DataSourceDefinition``` always
plays a role of a terminal node (a leaf) in a ```FeatureDefinition```/```Feature``` tree. Unlike ```FeatureDefinition```, ```DataSourceDefinition``` 
does not have any dependencies and does not perform any feature calculations - the purpose of this class is to hold metadata about
event schema, possible preprocessing steps and other info. Let's take a look at an example ```DataSourceDefinition```


```
class MyDataSourceDefinition(DataSourceDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        # This method defines schema of the event
        raise NotImplemented

    @classmethod
    def preprocess_impl(cls, raw_df: DataFrame) -> DataFrame:
        # Any preprocessing logic to get a sequence of EventSchema-like
        # records in a form of a DataFrame from raw data (raw_df)
        raise NotImplemented
```

See CryptotickL2BookIncrementalData for an example of a data source representing 
incremental order book updates from Cryptotick data provider.

## Data Ingest Pipeline

Featurizer provides a scalable, configurable and extensible data ingest pipeline
which takes raw user data and puts it in Featurizer storage. It takes care of such
things as indexing, compaction, per-data type resource allocation and many other data
engineering related problems. It integrates with DataSourceDefinition class so users
can easily add their own processing logic in a modular way without spinning up and maintaining
data engineering infrastructure.

TODO proper API and configuration for pipeline