## Feature Transforms

Featurizer provides a set of built-in operators for common transformations on time-series data called **Transforms**

Some examples are:

- **[diff](https://github.com/anovv/svoe/blob/main/featurizer/features/definitions/transforms/diff/diff.py)** - transforms time-series into a series of differences between sequential events
- **[min_max_scaling](WIP)** - scales values between 0 and 1 based on min and max value in a window
- **[ewma](WIP)** - exponential smoothing

Transforms are similar to regular FeatureDefinitions when coming to definition (they subclass ```FeatureDefinition```), however
differ in how they are used in ```FeaturizerConfig```: unlike regular ```FeatureDefinition``` which do not need direct specification
of dependant features (they are constructed automatically), Transforms require specific definition of dependencies:

```
feature_configs:
  - feature_definition: transforms.diff
    name: diff_mid_price
    deps:
      - mid_price
    params:
        ...
  - feature_definition: price.mid_price
    name: mid_price
    params:
        ...
```

## Creating new transforms

WIP

