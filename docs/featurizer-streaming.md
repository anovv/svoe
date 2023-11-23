# Featurizer Real Time Streaming

## Overview

One of the most powerful tools of Featurizer is the ability to seamlessly switch
between batch and real-time data processing without changing feature calculation code.

Featurizer provides a set of user-facing classes to build, launch and scale real-time streaming pipelines.
It is built using **[Streamz](https://github.com/python-streamz/streamz)** library to declaratively define event processing logic and 
**[Ray Actors](https://docs.ray.io/en/latest/ray-core/actors.html)** to scale the workload across cluster/CPUs.

## Event Emitters

[```DataSourceEventEmitter```](https://github.com/anovv/svoe/blob/main/featurizer/feature_stream/event_emitter/data_source_event_emitter.py) is a foundation of any streaming pipeline. Users define logic to emit ```Event``` objects and how to
register an arbitrary callback per feature. When building a pipeline from config, Featurizer automatically 
registers all necessary callbacks to connect dependent Features and calculation nodes (in case of a
distributed run)


```
class DataSourceEventEmitter:

    @classmethod
    def instance(cls) -> 'DataSourceEventEmitter':
        raise NotImplementedError

    def register_callback(self, feature: Feature, callback: Callable[[Feature, Event], Optional[Any]]):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError
```

By default, Featurizer uses [```CryptofeedEventEmitter```](https://github.com/anovv/svoe/blob/main/featurizer/feature_stream/event_emitter/cryptofeed_event_emitter.py)
which is based on a popular **[Cryptofeed](https://github.com/bmoscon/cryptofeed)** library.


##  FeatureStreamGraph

[```FeatureStreamGraph```](https://github.com/anovv/svoe/blob/main/featurizer/feature_stream/feature_stream_graph.py) 
is a class providing simple way to build a streaming pipeline in a non-distributed setting (i.e 1 worker)

```
fsg = FeatureStreamGraph(
    features_or_config: Union[List[Feature], FeaturizerConfig],
    combine_outputs: bool = False,
    combined_out_callback: Optional[Callable[[GroupedNamedDataEvent], Any]] = None
)
```

It uses **[Streamz](https://github.com/python-streamz/streamz)** library to connect Stream objects into a graph.

- ```combine_outputs``` defines whether output Feature streams should be merged into one

- If ```combine_outputs is True```, ```combined_out_callback: Callable[[GroupedNamedDataEvent], Any]``` parameter 
contains user-defined logic to process newly produced combined event. 
```GroupedNamedDataEvent``` describes data events for all features grouped into a single object. 
This is useful for real-time ML inference, where models expect all feature values in a single request

There are a number of useful methods to build custom pipelines:

- ```
  def emit_named_data_event(self, named_event: NamedDataEvent)
  ```
  
    Emits new event into the graph

- ```
  def set_callback(self, feature: Feature, callback: Callable[[Feature, Event], Optional[Any]])
  ```
  
    Sets custom callback per feature event


- ```
  def get_ins(self) -> List[Feature]
  ```
  
    Lists input feature streams

- ```
  def get_outs(self) -> List[Feature]
  ```
  
    Lists output feature streams

- ```
  def get_stream(self, feature: Feature) -> Stream
  ```
  
    Gets stream for feature


When initialized with a ```FeaturizerConfig```, Featurizer automatically builds necessary ```FeatureStreamGraph``` objects and
connects them with corresponding Event Emitters/ 

## Data Recording

Users can configure Featurizer to store features/data sources events to Featurizer Storage for further processing.
See **[Featurizer Real Time Data Recording](https://anovv.github.io/svoe/featurizer-real-time-data-recording/)**.

## Simulating real-time stream from offline data with OfflineFeatureStreamGenerator

For backtesting/simulation/ML model validation purposes, we often need to be able to simulate
a data stream from stored events. Featurizer provides OfflineFeatureStreamGenerator class, which
implements a typical generator interface and can be used to run custom logic over stored
data stream.

Work In Progress (make OfflineFeatureEventEmitter)

```
OfflineFeatureStreamGenerator example
```

See more in ```featurizer.feature_stream.offline_feature_stream_generator.py```


## Scalability

WIP

```FeatureStreamWorkerGraph```

```ScalingStrategy```

```FeaturizerStreamWorkerActor``` and ```FeaturizerStreamManagerActor```

```Transport```



## Fault Tolerance

Work In Progress

## Visualization

Work In Progress

