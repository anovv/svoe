from typing import List, Dict

import pandas as pd
import ray

from data_catalog.common.actors.db import DbActor
from data_catalog.common.data_models.models import InputItemBatch
from data_catalog.common.utils.sql.models import DataCatalog
from utils.pandas import df_utils


# @ray.remote
# def gather_and_wait(args):
#     return ray.get(args)
#
#
# # used to pipe dag nodes which outputs do not depend on each other
# @ray.remote
# def chain_no_ret(*args):
#     return args[0]
#
#
# @ray.remote
# def write_batch(db_actor: DbActor, batch: List[DataCatalog]) -> Dict:
#     return ray.get(db_actor.write_batch.remote(batch))
#
#
# @ray.remote
# def filter_existing(db_actor: DbActor, input_batch: InputItemBatch) -> InputItemBatch:
#     return ray.get(db_actor.filter_batch.remote(input_batch))

