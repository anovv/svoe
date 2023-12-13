from enum import Enum
from typing import List, Optional, Union, Type, Tuple

import yaml
from pydantic import BaseModel

from svoe.common.common_utils import load_class_by_name
from svoe.featurizer.data_definitions.data_source_definition import DataSourceDefinition

class DataProviderName(str, Enum):
    CRYPTOTICK = 'cryptotick'

class FeaturizerDataSourceFiles(BaseModel):
    data_source_definition: Union[str, Type[DataSourceDefinition]]
    files: Optional[List[str]]
    files_and_sizes: Optional[Union[List, Tuple[str, int]]]


class FeaturizerDataIngestConfig(BaseModel):
    provider_name: str
    batch_size: int
    max_executing_tasks: int
    data_source_files: List[FeaturizerDataSourceFiles]

    def num_files(self) -> int:
        res = 0
        for ds_files in self.data_source_files:
            if ds_files.files is not None:
                res += len(ds_files.files)
            else:
                res += len(ds_files.files_and_sizes)
        return res

    @classmethod
    def load_config(cls, path: str) -> 'FeaturizerDataIngestConfig':
        with open(path, 'r') as stream:
            d = yaml.safe_load(stream)
            c: FeaturizerDataIngestConfig = FeaturizerDataIngestConfig.parse_obj(d)
            for fs in c.data_source_files:
                if isinstance(fs.data_source_definition, str):
                    fs.data_source_definition = load_class_by_name(fs.data_source_definition)
                if fs.files is None and fs.files_and_sizes is None:
                    raise ValueError(f'Should provide either files or files_and_sizes for {fs.data_source_definition}')

                # tuplize files_and_sizes
                if fs.files_and_sizes is not None:
                    tuplized_files_and_sizes = []
                    for f in fs.files_and_sizes:
                        tuplized_files_and_sizes.append(tuple(f))
                    fs.files_and_sizes = tuplized_files_and_sizes
            return c

