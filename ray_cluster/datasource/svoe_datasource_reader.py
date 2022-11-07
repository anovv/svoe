from typing import Any, Dict, List, Optional
from ray.data.datasource.datasource import Datasource, Reader, ReadTask
from ray.data.block import BlockMetadata
from ray.data.block import Block
from featurizer.features.loader.df_utils import load_single_file


def _read_single_file(file_path) -> Block:
    return load_single_file(file_path)


class SvoeDatasourceReader(Reader):
    # This is constructed by the MongoDatasource, which will supply these args
    # about MongoDB.
    def __init__(self, file_paths: List[str]):
        self._file_paths = file_paths

    def get_read_tasks(self, parallelism: int) -> List[ReadTask]:
        read_tasks: List[ReadTask] = []
        for file_path in self._file_paths:
            # The metadata about the block that we know prior to actually executing
            # the read task.
            # TODO index metadata
            metadata = BlockMetadata(
                num_rows=None,
                size_bytes=None,
                schema=None,
                input_files=None,
                exec_stats=None,
            )
            # Supply a no-arg read function (which returns a block) and pre-read
            # block metadata.
            read_task = ReadTask(
                lambda file_path=file_path: [
                    _read_single_file(file_path)
                ],
                metadata,
            )
            read_tasks.append(read_task)
        return read_tasks
