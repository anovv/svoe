
from featurizer.features.data.data_source_definition import DataSourceDefinition
from featurizer.features.definitions.feature_definition import FeatureDefinition
from typing import Type, Dict, List, Callable, Union
from anytree import NodeMixin


class Feature(NodeMixin):
    def __init__(self, children: List['Feature'], position: int, feature_definition: Type[Union[DataSourceDefinition, FeatureDefinition]], params: Dict):
        self.children = children
        self.position = position
        self.feature_definition = feature_definition
        self.params = params
        self.feature_id = self._feature_id()

    def __hash__(self):
        return hash(self.feature_id)

    def __eq__(self, other):
        return self.feature_id == other.feature_id

    def __repr__(self):
        return self.feature_id

    def _feature_id(self) -> str:
        # TODO figure out how to pass data_params dependencies to features to get unique id
        if self.feature_definition.is_data_source():
            return f'data-source-{self.feature_definition.__name__}-{self.position}'
        else:
            return f'feature-{self.feature_definition.__name__}-{self.position}'


def construct_feature_tree(
    root_def: Type[Union[DataSourceDefinition, FeatureDefinition]],
    data_params: Union[Dict, List],
    feature_params: Union[Dict, List]
) -> Feature:
    return _construct_feature_tree(root_def, [0], [0], data_params, feature_params)


# traverse DataDefinition tree to construct parametrized FeatureTree
def _construct_feature_tree(
    root_def: Type[Union[DataSourceDefinition, FeatureDefinition]],
    feature_position_ref: List[int],
    data_position_ref: List[int],
    data_params: Union[Dict, List],
    feature_params: Union[Dict, List]
) -> Feature:
    if root_def.is_data_source():
        params = None
        position = data_position_ref[0]
        if position not in data_params:
            # TODO raise
            print('No data params specified')
            pass
        else:
            params = data_params[position]
        data_position_ref[0] += 1
        return Feature(
            children=[],
            position=position,
            feature_definition=root_def,
            params=params
        )

    deps = root_def.dep_upstream_schema()
    children = []
    for dep_fd in deps:
        if not dep_fd.is_data_source():
            feature_position_ref[0] += 1
        children.append(_construct_feature_tree(dep_fd, feature_position_ref, data_position_ref, data_params, feature_params))

    params = None
    position = feature_position_ref[0]
    if position not in feature_params:
        # TODO raise
        print('No feature params specified')
        pass
    else:
        params = feature_params[position]

    feature = Feature(
        children=children,
        position=position,
        feature_definition=root_def,
        params=params
    )
    feature_position_ref[0] -= 1
    return feature

# TODO use anytree api
def postorder(node: Feature, callback: Callable):
    if node.children is None or len(node.children) == 0:
        callback(node)
        return
    for child in node.children:
        postorder(child, callback)
    callback(node)
