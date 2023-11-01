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
