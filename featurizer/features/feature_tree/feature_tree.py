import joblib
from streamz import Stream

from typing import Dict, List, Callable, Union, Tuple, Type, Set, Optional
from anytree import NodeMixin
from copy import deepcopy

from featurizer.data_definitions.data_definition import DataDefinition
from featurizer.featurizer_utils.definitions_loader import DefinitionsLoader


class Feature(NodeMixin):
    def __init__(self, children: List['Feature'], data_definition: Type[DataDefinition], params: Dict):
        self.children = children
        self.data_definition = data_definition
        self.params = params
        self._is_label = False

        # TODO is it ok to call these at init time? Are all the children ready?
        self._data_deps = None
        self._data_deps = self.get_data_deps()
        self.key = self._key()

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        return self.key == other.key

    def __repr__(self):
        short_key = self.key[:8]
        if self._is_label:
            return f'label-{self.data_definition.__name__}-{short_key}'
        elif self.data_definition.is_data_source():
            return f'data-source-{self.data_definition.__name__}-{short_key}'
        else:
            return f'feature-{self.data_definition.__name__}-{short_key}'

    def _key(self) -> str:
        if self.data_definition.is_data_source():
            return joblib.hash([self.data_definition.__name__, self.params])

        data_deps = self.get_data_deps()
        feature_deps = self.get_inorder_feature_deps()
        dep_data_params = [d.params for d in data_deps]
        dep_feature_params = [f.params for f in feature_deps]

        # TODO add current and dep feature_definition versions to hash
        # TODO prev feature/data dep keys should also be a part of the key
        # TODO data_deps/feature_deps class types should also be part of the key
        return joblib.hash([self._is_label, self.data_definition.__name__, dep_data_params, dep_feature_params])

    def get_data_deps(self) -> List['Feature']:
        if self._data_deps is not None:
            return self._data_deps

        data_leafs = []
        def callback(node):
            if node.data_definition.is_data_source():
                data_leafs.append(node)

        postorder(self, callback)
        self._data_deps = data_leafs
        return self._data_deps

    def get_inorder_feature_deps(self) -> List['Feature']:
        deps = []
        def callback(node):
            if not node.data_definition.is_data_source():
                deps.append(node)
        inorder(self, callback)
        return deps

    def is_label(self) -> bool:
        return self._is_label

    @classmethod
    def make_label(cls, feature: 'Feature') -> 'Feature':
        c = deepcopy(feature)
        c._is_label = True
        # recalc feature key
        c.key = c._key()
        return c


def construct_feature_tree(
    root_def_name: Union[str, Type[DataDefinition]],
    params: Dict,
    existing_features: Dict[str, Feature] = {},
) -> Feature:
    data_source_params: Union[Dict, List] = params['data_source']
    feature_params: Union[Dict, List] = params['feature']
    return _construct_feature_tree(root_def_name, [0], [0], data_source_params, feature_params, existing_features)


# traverse DataDefinition tree to construct parametrized FeatureTree
def _construct_feature_tree(
    root_def_name: Union[str, Type[DataDefinition]],
    feature_position_ref: List[int],
    data_source_position_ref: List[int],
    data_source_params: Union[Dict, List],
    feature_params: Union[Dict, List],
    existing_features: Optional[Dict[str, Feature]] = None,
) -> Feature:
    if isinstance(root_def_name, str):
        root_def = DefinitionsLoader.load(root_def_name)
    else:
        root_def = root_def_name
    # TODO deprecate is_data_source, use isinstance
    if root_def.is_data_source():
        position = data_source_position_ref[0]
        data_source_position_ref[0] += 1
        f = Feature(
            children=[],
            data_definition=root_def,
            params=_parse_params(data_source_params, position)
        )
        if existing_features is None:
            return f
        if f.key in existing_features:
            return existing_features[f.key]
        else:
            existing_features[f.key] = f
            return f

    position = feature_position_ref[0]
    params = _parse_params(feature_params, position)
    dep_schema = params.get('dep_schema', None)
    # TODO cast to feature_definition
    deps = root_def.dep_upstream_definitions(dep_schema)
    children = []
    for dep_fd in deps:
        if not dep_fd.is_data_source():
            feature_position_ref[0] += 1
        children.append(_construct_feature_tree(dep_fd, feature_position_ref, data_source_position_ref, data_source_params, feature_params))

    f = Feature(
        children=children,
        data_definition=root_def,
        params=params
    )
    feature_position_ref[0] -= 1
    if existing_features is None:
        return f
    if f.key in existing_features:
        return existing_features[f.key]
    else:
        existing_features[f.key] = f
        return f


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


def inorder(node: Feature, callback: Callable):
    if node.children is None or len(node.children) == 0:
        callback(node)
        return
    callback(node)
    for child in node.children:
        inorder(child, callback)


def construct_stream_tree(feature: Feature) -> Tuple[Stream, Dict[Feature, Stream]]:
    data_streams = {}
    _, s = _construct_stream_tree(feature, data_streams)
    return s, data_streams


def _construct_stream_tree(feature: Feature, data_streams: Dict[Feature, Stream]) -> Tuple[Feature, Stream]:
    if feature.children is None or len(feature.children) == 0:
        # data node
        s = Stream()
        if feature in data_streams:
            raise ValueError('[Stream Tree] Duplicate data streams')
        data_streams[feature] = s
        return feature, s

    # upstreams = {dep_feature: Stream() for dep_feature in deps.keys()}
    upstreams = {}
    for child in feature.children:
        _, stream = _construct_stream_tree(child, data_streams)
        upstreams[child] = stream

    # TODO unify feature_definition.stream return type
    s = feature.data_definition.stream(upstreams, feature.params)
    if isinstance(s, Tuple):
        out_stream = s[0]
        state = s[1]
    else:
        out_stream = s
    return feature, out_stream
