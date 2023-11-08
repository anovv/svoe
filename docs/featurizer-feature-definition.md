# Features and Feature Definitions

## Overview

**Feature** is defined as an independent time based process, a set of timestamped events with identical schemas and contextual meaning,
which in the context of our framework are represented either as a real-time stream of events (in case of real-time processing) or
as a sequence of recorded events, stored as a (possibly distributed) dataframe (in case of historical/batch processing)

**Feature Definition** is an abstraction to define a blueprint for a time-series based
feature in a modular way. In this contex, you can view a separate feature as a result of applying feature-sepicfic
params to feature definition, i.e. ```Feature = FeatureDefinition + params```

In code, these abstractions are represented as ```Feature``` and ```FeatureDefinition``` classes. Users are not supposed to 
construct ```Feature``` objects directly and are expected to either use existing feature definitions or to implement their own
by subclassing ```FeatureDefinition```.

## FeatureDefinition overview

```FeatureDefinition```  is a base class for all custom feature definitions. To implement a new feature definition, user
must subclass it and implement key methods. Here is an example

```
class MyFeatureDefinitionFD(FeatureDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        # This method defines schema of the event
        raise NotImplemented

    @classmethod
    def stream(
        cls,
        dep_upstreams: Dict['Feature', Stream],
        feature_params: Dict
    ) -> Union[Stream, Tuple[Stream, Any]]:
        # Contains logic to compute events for this feature based on upstream
        # dependencies and user-provided params.
        # Uses Streamz library for declarative stream processing API
        raise NotImplemented

    @classmethod
    def dep_upstream_schema(
        cls, 
        dep_schema: str = Optional[None]
    ) -> List[Union[str, Type[DataDefinition]]]:
        # Specifies upstream dependencies for this FeatureDefinition as a list
        # of DataDefinition's
        raise NotImplemented

    @classmethod
    def group_dep_ranges(
        cls,
        feature: Feature,
        dep_ranges: Dict[Feature, List[BlockMeta]]
    ) -> IntervalDict:
        # Logic to group dependant input data (dep_ranges) into atomic blocks 
        # for parallel bulk processing of each group. The most basic case is 
        # identity_grouping(...): newly produced data blocks depend only on 
        # the current block (i.e. simple map operation)
        # For more complicated example, consider feature with 1 dependency, 
        # which produces window-aggregated calculations: here, for each new 
        # data block, we need to group all the dependant blocks which fall 
        # into that window (this is implemented in windowed_grouping(...) method)
        # There are other more complicated cases, for example time buckets of 
        # fixed lengths (for OHLCV as an example), and custom groupings based
        # on data blocks content (see L2SnapshotFD as an example)
        raise NotImplemented

```

As can be seen from the example above, ```FeatureDefintion``` class describes a tree-like structure,
where the root is the current ```FeatureDefintion``` and the leafs are ```DataSourceDefinition``` classes which
produce all the dependent features. Similarly, when framework builds ```Feature``` objects, each object is a
tree-like structure, uniquely identified by it's dependencies and parameters (see ```Feature``` class for more info).

For more examples please see examples section

## Defining parameters (feature_params and data_params)

WIP
