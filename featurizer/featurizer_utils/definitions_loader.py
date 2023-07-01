import concurrent.futures
from typing import Type, List, Tuple, Optional

from client.featurizer_client.featurizer_client import FeaturizerClient
from featurizer.data_definitions.data_definition import DataDefinition

import featurizer.features.definitions

import humps

import sys

DEFINITIONS_PATH = '/tmp/svoe_feature_definitions'
sys.path.append(DEFINITIONS_PATH)


class DefinitionsLoader:
    LOADER = None

    def __init__(self):
        self.featurizer_client = FeaturizerClient()
        self.futures = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=32)

    def _parse_definition_name(self, fd_name: str) -> Tuple[str, str, str]:
        # gets group, name, version from fd_name
        # TODO version
        s = fd_name.split('.')
        return s[0], s[1], '1'

    def _load_local_class(self, fd_name: str) -> Optional[Type[DataDefinition]]:
        group, definition, version = self._parse_definition_name(fd_name)
        class_name = humps.pascalize(definition)
        # ...Fd -> ...FD
        class_name = class_name.removesuffix('Fd')
        class_name = f'{class_name}FD'

        fd_module = None

        # TODO version
        # first check if given definition can be located in feature.definitions. (i.e. common feature defs like l2_snapshot_fd)
        common_definitions_module_name = featurizer.features.definitions.__name__
        # first {definition} for module, second {definition} for .py file
        common_definitions_fd_module_name = f'{common_definitions_module_name}.{group}.{definition}.{definition}'

        try:
            fd_module = __import__(common_definitions_fd_module_name, fromlist=[class_name])
        except:
            print(f'Unable to load {common_definitions_fd_module_name} locally')
            pass

        # then check if it can be found in already remote loaded fds
        remote_loaded_module_name = f'{group}.{definition}.{definition}'
        try:
            fd_module = __import__(remote_loaded_module_name, fromlist=[class_name])
        except:
            pass

        if fd_module is not None:
            return getattr(fd_module, class_name)
        else:
            return None

    def _load_many(self, fd_names: List[str]) -> List[Type[DataDefinition]]:
        fd_name_to_class = {}
        for fd_name in fd_names:
            clazz = self._load_local_class(fd_name)
            if clazz is not None:
                fd_name_to_class[fd_name] = clazz
            else:
                if fd_name not in self.futures:
                    group, definition, version = self._parse_definition_name(fd_name)

                    # TODO version
                    extract_path = f'{DEFINITIONS_PATH}/{group}/{definition}'
                    def _load_remote() -> Optional[str]:
                        return self.featurizer_client.load_feature_definition(
                            feature_group=group,
                            feature_definition=definition,
                            version=version,
                            extract_path=extract_path
                        )

                    self.futures[fd_name] = self.executor.submit(_load_remote)

        for fd_name in fd_names:
            if fd_name in self.futures:
                extract_path = self.futures[fd_name].result()
                if extract_path is None:
                    raise ValueError(f'Unable to load remote {fd_name}')

                # at this point remote fd should be loaded
                clazz = self._load_local_class(fd_name)
                if clazz is None:
                    raise ValueError(f'Unable to locate remotely loaded {fd_name}')

                fd_name_to_class[fd_name] = clazz

        res = []
        for fd_name in fd_names:
            if fd_name not in fd_name_to_class:
                raise ValueError(f'{fd_name} were not processed')
            res.append(fd_name_to_class[fd_name])
        return res

    @staticmethod
    def instance() -> 'DefinitionsLoader':
        if DefinitionsLoader.LOADER is not None:
            return DefinitionsLoader.LOADER
        DefinitionsLoader.LOADER = DefinitionsLoader()
        return DefinitionsLoader.LOADER

    @staticmethod
    def load(fd_name: str) -> Type[DataDefinition]:
        return DefinitionsLoader.load_many([fd_name])[0]

    @staticmethod
    def load_many(fd_names: List[str]) -> List[Type[DataDefinition]]:
        print(f'Loading definitions {fd_names}...')
        loader = DefinitionsLoader.instance()
        res = loader._load_many(fd_names)
        print(f'Finished loading definitions')
        return res


if __name__ == '__main__':
    defs1 = DefinitionsLoader.load('tvi.trade_volume_imb_fd')
    print(defs1)





