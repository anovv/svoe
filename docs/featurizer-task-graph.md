# Featurizer Task Graph

## Overview

The core of Featurizer's offline feature calculation is in building and executing Task Graph.

Task Graph is a graph of load, preprocess and user-defined feature specific calculation logic tasks
automatically built by the framework.

## How Building FeatureSet Graph Works

As mentioned in **Features and Feature Definitions** section, each ```Feature``` is a tree-like structure with
```DataSource``` leafs, dependent features as nodes and target feature as a root.
When user defines all necessary features in a ```FeaturizerConfig```, the framework builds all the
feature trees and their interdependencies and then maps corresponding feature calculation tasks (which are
defined by ```FeatureDefinition:stream``` method) and data source load tasks into a graph. The tasks are intorconnected
by passing dataframes as inputs and returns which are stored in Ray's distributed memory

TODO explain range blocks



See more in ```featurizer.task_graph.builder.py```

## Label + FeatureSet = FeatureLabelSet Graph

If user 

## Point-in-time Joins