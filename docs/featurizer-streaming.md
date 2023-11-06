# Featurizer Real Time Streaming

## Overview

One of the most powerful tools of Featurizer is the ability to seamlessly switch
between batch and real-time data processing withour changing feature calculation code.

For real-time feature calculation and offline simulation, Featurizer provides a set of convenient classes.

## Real-time streaming with FeatureStreamGraph

```FeatureStreamGraph``` is a class providing simple way to build a streaming pipeline

```
fsg = FeatureStreamGraph(
    features_or_config: Union[List[Feature], FeaturizerConfig]=my_features_or_config,
    callback: Callable[[GroupedNamedDataEvent], Any]=mycallback
)
```

To emit events into the graph simply call

```
fsg.emit_named_data_event(named_data_event: NamedDataEvent)
```

where ```NamedDataEvent``` is a tuple of Feature (data source) object and a dict

```callback: Callable[[GroupedNamedDataEvent], Any]``` parameter contains user-defined logic to process newly 
produced event. ```GroupedNamedDataEvent``` describes data events for all features grouped into a single object. 
This is useful for real-time ML inference, where models expect all feature values in a single request

See more in ```featurizer.feature_stream.feature_stream_graph.py```


## Simulating real-time stream from offline data with OfflineFeatureStreamGenerator

For backtesting/simulation/ML model validation purposes, we often need to be able to simulate
a data stream from stored events. Featurizer provides OfflineFeatureStreamGenerator class, which
implements a typical generator interface and can be used to run custom logic over stored
data stream.

Work In Progress 

```
OfflineFeatureStreamGenerator example
```

See more in ```featurizer.feature_stream.offline_feature_stream_generator.py```


## Scalability

Oftentimes user may want to use configs which calculate thousand , which  . For now Featurizer does not provide (although this is one of the
highest )

## Fault Tolerance

Work In Progress

## Visualization

Work In Progress

