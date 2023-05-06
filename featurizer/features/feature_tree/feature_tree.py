from streamz import Stream

from featurizer.data_catalog.api.api import DataKey, data_key
from featurizer.data_definitions.data_source_definition import DataSourceDefinition
from featurizer.features.definitions.feature_definition import FeatureDefinition
from typing import Type, Dict, List, Callable, Union, Tuple
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

    def get_data_deps(self) -> List['Feature']:
        data_leafs = []
        def callback(node):
            if node.feature_definition.is_data_source():
                data_leafs.append(node)

        postorder(self, callback)
        return data_leafs

    # TODO move this to FeatureDefinition package
    def build_stream_graph(self) -> Dict['Feature', Stream]:
        stream_graph = {}

        def callback(feature: Feature):
            if feature.feature_definition.is_data_source():
                stream_graph[feature] = Stream()
                return
            dep_upstreams = {}
            for dep_feature in feature.children:
                dep_upstreams[dep_feature] = stream_graph[dep_feature]
            # TODO this should be part of Feature class
            s = feature.feature_definition.stream(dep_upstreams, feature.params)
            if isinstance(s, Tuple):
                stream = s[0]
                state = s[1]
            else:
                stream = s
            stream_graph[feature] = stream

        postorder(self, callback)
        return stream_graph



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
        position = data_position_ref[0]
        data_position_ref[0] += 1
        return Feature(
            children=[],
            position=position,
            feature_definition=root_def,
            params=_parse_params(data_params, position)
        )

    position = feature_position_ref[0]
    params = _parse_params(feature_params, position)
    dep_schema = params.get('dep_schema', None)
    print(dep_schema)
    deps = root_def.dep_upstream_schema(dep_schema)
    children = []
    for dep_fd in deps:
        if not dep_fd.is_data_source():
            feature_position_ref[0] += 1
        children.append(_construct_feature_tree(dep_fd, feature_position_ref, data_position_ref, data_params, feature_params))

    feature = Feature(
        children=children,
        position=position,
        feature_definition=root_def,
        params=params
    )
    feature_position_ref[0] -= 1
    return feature


def _parse_params(params: Union[Dict, List], position: int):
    if params is None:
        return {}

    if isinstance(params, Dict):
        return params.get(position, {})

    if isinstance(params, List):
        if position <= len(params):
            return params[position]
        else:
            raise ValueError(f'Position {position} is larger then params len: {len(params)}')

    raise ValueError(f'Unsupported params type: {type(params)}')



# TODO use anytree api
def postorder(node: Feature, callback: Callable):
    if node.children is None or len(node.children) == 0:
        callback(node)
        return
    for child in node.children:
        postorder(child, callback)
    callback(node)
