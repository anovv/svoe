# Featurizer Quick Start

Featurizer helps creating distributed ```FeatureLabelSet``` dataframes from [Feature Definitions]() to be used for analysis, ML training
and real-time streaming.

Here is an example to construct [mid-price](https://en.wikipedia.org/wiki/Mid_price) and volatility features from 
partial order book updates, 5 second lookahead label as prediction target, using 1 second granularity data

- Pick existing or define your own ```FeatureDefinition``` (see [Feature Definitions]() section)
    - Create ```FeaturizerConfig```
        - Define start and end dates (more in Data Model)
        - Pick which features to store by setting ```to_store``` (more in Storage)
        - Define label feature by setting ```label_feature_index``` and ```label_lookahead``` (more in Labeling)
        - Define features in ```feature_configs```. Each feature is a result of applying ```params:feature``` and 
          ```params:data_source``` to ```FeatureDefinition```
  
        Example config:
    
        ```
        start_date: '2023-02-01 10:00:00'
        end_date: '2023-02-01 11:00:00'
        label_feature_index: 0
        label_lookahead: '5s'
        features_to_store: [0, 1]
        feature_configs:
          - feature_definition: price.mid_price_fd.MidPriceFD
            name: mid_price
            params:
              data_source: &id001
                - exchange: BINANCE
                  instrument_type: spot
                  symbol: BTC-USDT
              feature:
                sampling: 1s
          - feature_definition: volatility.volatility_stddev_fd.VolatilityStddevFD
            params
              data_source: *id001
              feature:
                sampling: 1s
        ```
        See [MidPriceFD](https://github.com/anovv/svoe/blob/main/featurizer/features/definitions/price/mid_price_fd/mid_price_fd.py) and [VolatilityStddevFD](https://github.com/anovv/svoe/blob/main/featurizer/features/definitions/volatility/volatility_stddev_fd/volatility_stddev_fd.py) for implementation details

- Run Featurizer
     
    === "CLI"
        ```
        svoe featurizer run <path_to_config> --ray-address <addr> --parallelism <num-workers>
        ```
    === "Python API"
        ```
        Featurizer.run(path=<path_to_config>, ray_address=<addr>, parallelism=<num_workers>)
        ```
  
    Featurizer will compile a graph of tasks, execute it in a distributed manner over the cluster and store
    the resulted distributed dataframe (```FeatureLabelSet```) in cluster memory and optionally in persistent storage.

- Get sampled results. Once calculation is finished, run following command to get sampled ```FeatureLabelSet``` dataframe into your local laptop memory
  
        
    === "CLI"
        ```
        svoe featurizer get-data --every-n <every_nth_row>
        ```
        
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
      
- Visualize the results
        
    === "CLI"
        ```
        svoe featurizer plot --every-n <every_nth_row>
        ```

  