## Backtester Quick Start

Once we have our best model from ***[Trainer](https://anovv.github.io/svoe/trainer-overview/)***, we can plug it in our ```BaseStrategy``` derived class and run ***[Backtester](https://anovv.github.io/svoe/backtester-overview/)***

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
      
    === "CLI"
        ```
        svoe backtester run --config-path <config-path> --ray-address <addr> --num-workers <num-workers>
        ```
    === "Python API"
        ```
        config = BacktesterConfig.load_config(config_path)
        backtester = Backtester.from_config(config)
        backtester.run_remotely(ray_address=ray_address, num_workers=num_workers)
        ```

  This will run a distributed event-driven backtest using features and models defined earlier

- Get statistics with 

    === "Python API"
        ```
        stats = backtester.get_stats()
        ```
