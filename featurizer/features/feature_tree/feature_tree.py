
from featurizer.features.data.data_definition import DataDefinition
from featurizer.features.data.data_source_definition import DataSourceDefinition
from featurizer.features.definitions.feature_definition import FeatureDefinition
from typing import Type, Dict, List, Callable, Union


class FeatureTreeNode:
    def __init__(self, children: List['FeatureTreeNode'], node_id: int, fd: Type[Union[DataSourceDefinition, FeatureDefinition]], params: Dict):
        self.children = children
        self.node_id = node_id
        self.fd = fd
        self.params = params


def _node_id(position: int, params: Dict) -> int:
    # TODO figure out how to pass data_params dependencies to features to get unique id
    return position


# traverse DataDefinition tree to construct parametrized FeatureTree
def construct_feature_tree(
    root_def: Type[Union[DataSourceDefinition, FeatureDefinition]],
    position_ref: List[int], # TODO have different position for data and feature
    data_params: Dict,
    feature_params: Dict
) -> FeatureTreeNode:
    if root_def.is_data_source():
        return FeatureTreeNode(
            children=[],
            node_id=_node_id(position_ref[0], data_params),
            fd=root_def,
            params=data_params[position_ref[0]]
        )

    deps = root_def.dep_upstream_schema()
    children = []
    for dep_fd in deps:
        position_ref[0] += 1
        children.append(construct_feature_tree(dep_fd, position_ref, data_params, feature_params))

    return FeatureTreeNode(
        children=children,
        node_id=_node_id(position_ref[0], feature_params),
        fd=root_def,
        params=feature_params[position_ref[0]]
    )


def postorder(node: FeatureTreeNode, callback: Callable):
    if node.children is None or len(node.children) == 0:
        callback(node)
        return
    for child in node.children:
        postorder(child, callback)

    callback(node)