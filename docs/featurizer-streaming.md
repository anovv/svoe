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

TODO OfflineFeatureStreamGenerator


## Scalability

TODO


