As an example, here is a simple 3 step tutorial to build a simple **[mid-price](https://en.wikipedia.org/wiki/Mid_price)** prediction model based on past price and volatility. 

- Run ***[Featurizer](https://anovv.github.io/svoe/featurizer-overview/)*** to construct mid-price and volatility features from partial order book updates, 5 second lookahead label as prediction target 
  - Define `featurizer-config.yaml`
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
          data: *id001
          feature:
            sampling: 1s
    ```
    See [MidPriceFD](https://github.com/anovv/svoe/blob/main/featurizer/features/definitions/price/mid_price_fd/mid_price_fd.py) and [VolatilityStddevFD](https://github.com/anovv/svoe/blob/main/featurizer/features/definitions/volatility/volatility_stddev_fd/volatility_stddev_fd.py) for implementation details
  - Run Featurizer
    - CLI: `svoe featurizer run <path_to_config> --ray-address <addr> --parallelism <num-workers>`
    - Python API: `Featurizer.run(path=<path_to_config>, ray_address=<addr>, parallelism=<num_workers>)`
  - Once calculation is finished, load sampled ```FeatureLabelSet``` dataframe to your local client
    - CLI: `svoe featurizer get-data --every-n <every_nth_row>`
    - Python API: `Featurizer.get_materialized_data(pick_every_nth_row=<every_nth_row>)`
    ```
          timestamp  receipt_timestamp  label_mid_price-mid_price  mid_price-mid_price  feature_VolatilityStddevFD_62271b09-volatility
    0     1.675234e+09       1.675234e+09                  23084.800            23084.435                                        0.000547
    1     1.675234e+09       1.675234e+09                  23083.760            23084.355                                        0.040003
    2     1.675234e+09       1.675234e+09                  23083.505            23084.635                                        0.117757
    3     1.675234e+09       1.675234e+09                  23084.610            23085.020                                        0.257091
    4     1.675234e+09       1.675234e+09                  23084.725            23084.800                                        0.242034
    ...            ...                ...                        ...                  ...                                             ...
    ```
  - We can also visualize the results
    - CLI: `svoe featurizer plot --every-n <every_nth_row>`
- Once we have our ```FeatureLabelSet``` calculated and loaded in cluster memory, let's use ***[Trainer](https://anovv.github.io/svoe/trainer-overview/)*** to train XGBoost model to predict mid-price 5 seconds ahead, validate the model, tune hyperparams and pick best model
  - Define config
    ```
    xgboost:
      params:
        tree_method: 'approx'
        objective: 'reg:linear'
        eval_metric: [ 'logloss', 'error' ]
      num_boost_rounds: 10
      train_valid_test_split: [0.5, 0.3]
    num_workers: 3
    tuner_config:
      param_space:
        params:
          max_depth:
            randint:
              lower: 2
              upper: 8
          min_child_weight:
            randint:
              lower: 1
              upper: 10
      num_samples: 8
      metric: 'train-logloss'
      mode: 'min'
    max_concurrent_trials: 3
    ```
  - Run Trainer
    - CLI: `svoe trainer run --config-path <config-path> --ray-address <addr>`
    - Python API: 
      ```
      config = TrainerConfig.load_config(config_path)
      trainer_manager = TrainerManager(config=config, ray_address=ray_address)
      trainer_manager.run(trainer_run_id='sample-run-id', tags={})
      ```
  - Visualize predictions
    - CLI: `svoe trainer predictions --model-uri <model-uri>`
  - Select best model
    - CLI: `svoe trainer best-model --metric-name valid-logloss --mode min`
    - Python API:
      ```
      mlflow_client = SvoeMLFlowClient()
      best-model-uri = mlflow_client.get_best_checkpoint_uri(metric_name=metric_name, experiment_name=experiment_name, mode=mode)
      ```
-  Once we have our best model, we can plug it in our ```BaseStrategy``` derived class and run ***[Backtester](https://anovv.github.io/svoe/backtester-overview/)***
  - Define config
    ```
    featurizer_config_path: featurizer-config.yaml
    portfolio_config: <portfolio_config>
    inference_config:
      model_uri: <your-best-model-uri>
      predictor_class_name: 'XGBoostPredictor'
      num_replicas: <number-of-predictor-replicas> 
    tradable_instruments_params:
      - exchange: 'BINANCE'
        instrument_type: 'spot'
        symbol: 'BTC-USDT'
    strategy_class_name: 'backtester.strategy.ml_strategy.MLStrategy'
    strategy_params:
      buy_delta: 0
      sell_delta: 0
    ```
    See [MLStrategy](https://github.com/anovv/svoe/blob/main/backtester/strategy/ml_strategy.py) for example implementation
  - Run Backtester
    - CLI: `svoe backtester run --config-path <config-path> --ray-address <addr> --num-workers <num-workers>`
    - Python API:
      ```
      config = BacktesterConfig.load_config(config_path)
      backtester = Backtester.from_config(config)
      backtester.run_remotely(ray_address=ray_address, num_workers=num_workers)
      ```
    This will run a distributed event-driven backtest using features and models defined earlier
  - Get stats with `backtester.get_stats()`
