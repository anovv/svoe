import joblib
from streamz import Stream

from typing import Dict, List, Callable, Union, Tuple, Type, Optional
from copy import deepcopy

from featurizer.config import FeatureConfig
from featurizer.data_definitions.data_definition import DataDefinition
from featurizer.featurizer_utils.definitions_loader import DefinitionsLoader


class Feature:
    def __init__(self, children: List['Feature'], data_definition: Type[DataDefinition], params: Dict, name: Optional[str] = None):
        self.children = children
        self.data_definition = data_definition
        self.params = params
        self.name = name
        self._is_label = False

        # TODO is it ok to call these at init time? Are all the children ready?
        self._data_deps = None
        self._data_deps = self.get_data_sources()
        self.key = _calculate_key(self)

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        return self.key == other.key

    def __repr__(self):
        if self.name is not None:
            return self.name
        short_key = self.key[:8]
        if self._is_label:
            return f'label_{self.data_definition.__name__}_{short_key}'
        elif self.data_definition.is_data_source():
            return f'data_source_{self.data_definition.__name__}_{short_key}'
        else:
            return f'feature_{self.data_definition.__name__}_{short_key}'

    def get_data_sources(self) -> List['Feature']:
        if self._data_deps is not None:
            return self._data_deps

        data_sources = []
        def callback(node):
            if node.data_definition.is_data_source():
                data_sources.append(node)

        postorder(self, callback)
        self._data_deps = data_sources
        return self._data_deps

    def get_dep_features_inorder(self) -> List['Feature']:
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
        l = deepcopy(feature)
        l._is_label = True
        if l.name is not None:
            l.name = 'label_' + l.name
        # recalc feature key
        l.key = _calculate_key(l)
        return l


def _calculate_key(feature: Feature) -> str:
    # TODO feature name should not be used as a hash? what if we have derived feature same as named?
    # if feature.name is not None:
    #     return joblib.hash(feature.name)
    # TODO update when versioning is supported
    dep_hashes = []
    for dep_feature in feature.children:
        dep_hashes.append(_calculate_key(dep_feature))

    # sort to make sure order of dep features does not matter
    dep_hashes.sort()
    h = [feature._is_label, feature.data_definition.__name__, feature.params]
    h.extend(dep_hashes)
    return joblib.hash(h)


def construct_features_from_configs(feature_configs: List[FeatureConfig]) -> List[Feature]:
    features = []
    existing_features = []
    configs = feature_configs
    while len(configs) != 0:
        num_configs = len(configs)
        for feature_config in configs:
            if feature_config.deps is None:
                # first construct derived features because they have no dependencies
                feature = construct_feature(
                    root_def_name=feature_config.feature_definition,
                    params=feature_config.params,
                    existing_features=existing_features,
                    name=feature_config.name
                )
                features.append(feature)

                # update existing features with current feature and all dependencies
                existing_features.append(feature)
                for dep_feature in feature.get_dep_features_inorder():
                    if dep_feature not in existing_features:
                        existing_features.append(dep_feature)
                for dep_data_source in feature.get_data_sources():
                    if dep_data_source not in existing_features:
                        existing_features.append(dep_data_source)
                configs.remove(feature_config)
                break
            else:
                # generic feature, check if we have all the necessary dependant features built
                has_all_deps = True
                for key_or_name in feature_config.deps:
                    dep_feature = get_feature_by_key_or_name(existing_features, key_or_name)
                    if dep_feature is None:
                        has_all_deps = False
                        break
                if has_all_deps:
                    feature = construct_feature(
                        root_def_name=feature_config.feature_definition,
                        params=feature_config.params,
                        existing_features=existing_features,
                        name=feature_config.name,
                        deps=feature_config.deps
                    )
                    features.append(feature)

                    # update existing features with current feature and all dependencies
                    existing_features.append(feature)
                    for dep_feature in feature.get_dep_features_inorder():
                        if dep_feature not in existing_features:
                            existing_features.append(dep_feature)
                    for dep_data_source in feature.get_data_sources():
                        if dep_data_source not in existing_features:
                            existing_features.append(dep_data_source)

                    configs.remove(feature_config)

        # none of the features were built in this iteration - malformed config
        if len(configs) == num_configs:
            raise ValueError(
                'Can not construct features for given config, make sure all features have proper dependencies')

    return features


def construct_feature(
    root_def_name: Union[str, Type[DataDefinition]],
    params: Dict,
    existing_features: List[Feature] = [],
    name: Optional[str] = None,
    deps: Optional[List[str]] = None,
) -> Feature:
    if isinstance(root_def_name, str):
        root_def = DefinitionsLoader.load(root_def_name)
    else:
        root_def = root_def_name
    if deps is not None:
        # generic feature
        dep_features = []
        for dep_key_or_name in deps:
            dep_feature = get_feature_by_key_or_name(existing_features, dep_key_or_name)
            if dep_feature is None:
                raise ValueError(f'Can not find feature for key_or_name: {dep_key_or_name}')
            dep_features.append(dep_feature)
        feature = Feature(children=dep_features, data_definition=root_def, params=params, name=name)
        if feature in existing_features:
            index = existing_features.index(feature)
            feature = existing_features[index]
        return feature

    data_source_params: Union[Dict, List] = params['data_source']
    feature_params: Union[Dict, List] = params.get('feature', None)
    return _construct_feature_tree(
        root_def=root_def,
        feature_position_ref=[0],
        data_source_position_ref=[0],
        data_source_params=data_source_params,
        feature_params=feature_params,
        existing_features=existing_features,
        name=name
    )


# traverse DataDefinition tree to construct parametrized FeatureTree
def _construct_feature_tree(
    root_def: Type[DataDefinition],
    feature_position_ref: List[int],
    data_source_position_ref: List[int],
    data_source_params: Union[Dict, List],
    feature_params: Optional[Union[Dict, List]],
    existing_features: List[Feature],
    name: Optional[str]
) -> Feature:
    # TODO deprecate is_data_source, use isinstance
    if root_def.is_data_source():
        position = data_source_position_ref[0]
        data_source_position_ref[0] += 1
        f = Feature(
            children=[],
            data_definition=root_def,
            params=_parse_params(data_source_params, position),
            name=name
        )
        if f in existing_features:
            index = existing_features.index(f)
            return existing_features[index]
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
        children.append(_construct_feature_tree(
            root_def=dep_fd,
            feature_position_ref=feature_position_ref,
            data_source_position_ref=data_source_position_ref,
            data_source_params=data_source_params,
            feature_params=feature_params,
            existing_features=existing_features,
            name=None
        ))

    f = Feature(
        children=children,
        data_definition=root_def,
        params=params,
        name=name
    )
    feature_position_ref[0] -= 1
    if f in existing_features:
        index = existing_features.index(f)
        return existing_features[index]
    return f


def get_feature_by_key_or_name(features: List[Feature], key_or_name: str) -> Optional[Feature]:
    for feature in features:
        if feature.key == key_or_name or feature.name == key_or_name:
            return feature

    return None


def _parse_params(params: Optional[Union[Dict, List]], position: int):
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


# TODO move to helper class
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
