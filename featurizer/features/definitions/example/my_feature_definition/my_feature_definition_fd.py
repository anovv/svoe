from typing import Dict, Union, Tuple, Any, Optional, List, Type

from portion import IntervalDict
from streamz import Stream

from featurizer.blocks.blocks import BlockMeta
from featurizer.data_definitions.data_definition import EventSchema, DataDefinition
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.feature_tree.feature_tree import Feature


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
        # Contains logic to compute events for this feature based on upstream dependencies and user-provided params.
        # Uses Streamz library for declarative stream processing API
        raise NotImplemented

    @classmethod
    def dep_upstream_schema(cls, dep_schema: str = Optional[None]) -> List[Union[str, Type[DataDefinition]]]:
        # Specifies upstream dependencies for this FeatureDefinition as a list of DataDefinition's
        raise NotImplemented

    @classmethod
    def group_dep_ranges(
        cls,
        feature: Feature,
        dep_ranges: Dict[Feature, List[BlockMeta]]
    ) -> IntervalDict:
        # Logic to group dependant input data (dep_ranges) into atomic blocks for parallel bulk processing of each group.
        # The most basic case is identity_grouping(...): newly produced data blocks depend only on current block (i.e. simple map
        # transformation)
        # For more complicated example, consider feature with 1 dependency, which produces window-aggregated calculations:
        # here, for each new data block, we need to group all the dependant blocks which fall into that window (this is implemented
        # in windowed_grouping(...) method)
        # There are other more complicated cases, for example time buckets of fixed lengths (for OHLCV as an example), and custom
        # groupings based on data blocks content (see L2SnapshotFD as an example)
        raise NotImplemented
