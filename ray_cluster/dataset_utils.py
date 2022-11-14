import ray

from typing import Optional, List, Dict, Any
from ray_cluster.datasource.svoe_datasource import SvoeDatasource
from ray.data.dataset import Dataset
from ray.data.context import DatasetContext

from featurizer.features.loader.l2_snapshot_utils import get_info


def read_files(file_paths: List[str], parallelism: Optional[int] = 100) -> Dataset:
    return ray.data.read_datasource(
        SvoeDatasource(),
        file_paths=file_paths,
        parallelism=parallelism
    )


def l2_deltas_info_per_block(l2_deltas_dataset: Dataset) -> List[Dict[str, Any]]:
    # use ds.take_all() to combine
    l2_deltas_dataset.get_internal_block_refs()
    return l2_deltas_dataset.map_batches(lambda df: get_info(df)).take_all()


def l2_deltas_partitioned_dataset(l2_deltas_dataset: Dataset) -> Dataset:
    info_per_block = l2_deltas_info_per_block(l2_deltas_dataset) # TODO load lazily
    # block_refs = l2_deltas_dataset.lazy().get_internal_block_refs()
    groups = []
    for block_index in range(0, len(info_per_block)):
        continue

