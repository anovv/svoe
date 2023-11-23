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
        
    @classmethod
    def event_emitter_type(cls) -> Type[DataSourceEventEmitter]:
        # provides DataSourceEventEmitter type associated with this data source
        raise NotImplemented
```

Some examples of common data source definitions

- [CryptotickL2BookIncrementalData](https://github.com/anovv/svoe/blob/main/featurizer/data_definitions/common/l2_book_incremental/cryptotick/cryptotick_l2_book_incremental.py) - incremental updates for L2 orderbook from [Cryptotick](https://www.cryptotick.com/) data provider

- [CryptofeedL2BookIncrementalData](https://github.com/anovv/svoe/blob/main/featurizer/data_definitions/common/l2_book_incremental/cryptofeed/cryptofeed_l2_book_incremental.py) - incremental updates for L2 orderbook from [Cryptofeed](https://github.com/bmoscon/cryptofeed) library

- [CryptofeedTickerData](https://github.com/anovv/svoe/blob/main/featurizer/data_definitions/common/ticker/cryptofeed/cryptofeed_ticker.py) - Cryptofeed ticker

- [CryptotickTradesData](https://github.com/anovv/svoe/blob/main/featurizer/data_definitions/common/trades/cryptotick/cryptotick_trades.py) - Cryptotick trades

- [CryptofeedTradesData](https://github.com/anovv/svoe/blob/main/featurizer/data_definitions/common/trades/cryptofeed/cryptofeed_trades.py) - Cryptofeed trades

See [Featurizer Real Time Streaming](https://anovv.github.io/svoe/featurizer-streaming/) for Event Emitter details
