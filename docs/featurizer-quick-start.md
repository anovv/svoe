# Featurizer Quick Start

- Pick existing or define your own FeatureDefinition (see more in Feature Definitions section)
- Create Featurizer Config
    * Define start and end dates (more in Data Model)
    * Pick which features to store by setting to_store (more in Storage)
    * Define label feature by setting lookahead_shift (more in Labeling)
    * Define features in feature_configs. Each feature is a result of applying feature_params and data_params 
      to FeatureDefinition.
  
  Example config:
  ```
  start_date: '2023-02-01 10:00:00'
  end_date: '2023-02-01 11:00:00'
  label_feature_index: 0
  label_lookahead: '5s'
  features_to_store: [0, 1]
  feature_configs:
    - feature_definition: price.mid_price_fd
      name: mid_price
      params:
        data_source: &id001
          - exchange: BINANCE
            instrument_type: spot
            symbol: BTC-USDT
        feature:
          1:
            dep_schema: cryptotick
            sampling: 1s
    - feature_definition: volatility.volatility_stddev_fd
      data_params: *id001
      feature_params:
        2:
          dep_schema: cryptotick
          sampling: 1s
  ```
- Run Featurizer
  * CLI: svoe featurizer run <path_to_config>
  * Python API: Featurizer.run(path='path_to_config')
  
  Featurizer will compile a graph of tasks, execute it in a distributed manner over the cluster and store
  the resulted distributed dataframe (FeatureLabelSet) in clutser memory and optionally in persistent storage.
  The above config will result in following dataframe: 
  
  ```
  TODO show dataframe here
  ```
  

  