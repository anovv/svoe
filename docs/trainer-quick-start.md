## Trainer Quick Start

Once we have our ```FeatureLabelSet``` calculated and loaded in cluster memory using ***[Featurizer](https://anovv.github.io/svoe/featurizer-overview/)***, let's use ***[Trainer](https://anovv.github.io/svoe/trainer-overview/)*** to train XGBoost model to predict mid-price 5 seconds ahead, validate the model, tune hyperparams and pick best model
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