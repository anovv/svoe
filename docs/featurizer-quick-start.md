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
  * CLI: ```svoe featurizer run <path_to_config>```
  * Python API: ```Featurizer.run(path='path_to_config')```
  
  Featurizer will compile a graph of tasks, execute it in a distributed manner over the cluster and store
  the resulted distributed dataframe (FeatureLabelSet) in cluster memory and optionally in persistent storage.
  The above config will result in following dataframe: 
  
  ```
          timestamp  receipt_timestamp  label_mid_price-mid_price  mid_price-mid_price  feature_VolatilityStddevFD_62271b09-volatility
  0     1.675234e+09       1.675234e+09                  23084.800            23084.435                                        0.000547
  1     1.675234e+09       1.675234e+09                  23083.760            23084.355                                        0.040003
  2     1.675234e+09       1.675234e+09                  23083.505            23084.635                                        0.117757
  3     1.675234e+09       1.675234e+09                  23084.610            23085.020                                        0.257091
  4     1.675234e+09       1.675234e+09                  23084.725            23084.800                                        0.242034
  ...            ...                ...                        ...                  ...                                             ...

  ```
  

  