import functools
from threading import Thread
from typing import Optional

import ray

from featurizer.data_ingest.config import FeaturizerDataIngestConfig, DataProviderName
from featurizer.data_ingest.pipelines.cryptotick.pipeline import CatalogCryptotickPipeline, poll_to_tqdm
from featurizer.data_ingest.utils.cryptotick_utils import cryptotick_input_items
from featurizer.sql.db_actor import create_db_actor


class FeaturizerDataIngestPipelineRunner:

    @classmethod
    def run(cls, config: Optional[FeaturizerDataIngestConfig] = None, path_to_config: Optional[str] = None, ray_address: str = 'auto'):
        if path_to_config is not None:
            config = FeaturizerDataIngestConfig.load_config(path_to_config)
        if config is None:
            raise ValueError('Should provide either config or path_to_config')

        with ray.init(address=ray_address, ignore_reinit_error=True):

            db_actor = create_db_actor()
            if config.provider_name == DataProviderName.CRYPTOTICK:
                pipeline = CatalogCryptotickPipeline.options(name='CatalogCryptotickPipeline').remote(
                    max_executing_tasks=config.max_executing_tasks,
                    db_actor=db_actor
                )
            else:
                raise ValueError(f'Unsupported data provider {config.provider_name}')

            batches = cryptotick_input_items(config)

            Thread(target=functools.partial(poll_to_tqdm, total_files=config.num_files(), chunk_size=100 * 1024)).start()
            pipeline.run.remote()
            print('Queueing batches...')

            for i in range(len(batches)):
                ray.get(pipeline.pipe_input.remote(batches[i]))
            print('Done queueing')
            # wait for everything to process
            ray.get(pipeline.wait_to_finish.remote())

