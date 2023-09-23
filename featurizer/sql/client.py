from typing import Optional, Dict, List
from common.db.sql_client import SqlClient, Session
from featurizer.data_catalog.common.data_models.models import InputItemBatch


from featurizer.sql.feature_def.models import FeatureDefinitionDB
from featurizer.sql.models.data_source_block_metadata import DataSourceBlockMetadata
from featurizer.sql.models.feature_block_metadata import FeatureBlockMetadata
from featurizer.sql.models.feature_metadata import FeatureMetadata


class FeaturizerSqlClient(SqlClient):
    def __init__(self):
        super(FeaturizerSqlClient, self).__init__()

    # TODO separate api methods and pipeline methods
    def write_block_metadata_batch(self, batch: List[DataSourceBlockMetadata | FeatureBlockMetadata]):
        # check for existing hashes
        # hashes = [i.hash for i in batch]
        session = Session()
        #
        # if isinstance(batch[0], DataCatalog):
        #     existing = session.query(DataCatalog).filter(DataCatalog.hash.in_(hashes)).all()
        # else:
        #     existing = session.query(FeatureCatalog).filter(FeatureCatalog.hash.in_(hashes)).all()
        #
        # existing_hashes = [i.hash for i in existing]
        # # filter existing
        # batch = [i for i in batch if i.hash not in existing_hashes]

        # TODO what if primary key exists? Override?
        session.bulk_save_objects(batch)

        # TODO try catch and handle
        # 1) connection issues
        # 2) duplicate entries
        session.commit()
        print(f'Written {len(batch)} index items to Db')
        return # TODO return result?

    def filter_cryptotick_batch(self, batch: InputItemBatch) -> InputItemBatch:
        items = batch[1]
        meta = batch[0]
        paths = [item[DataSourceBlockMetadata.path.name] for item in items]
        session = Session()
        query_in = DataSourceBlockMetadata.extras['source_path'].in_(paths)
        select_in_db = session.query(DataSourceBlockMetadata).filter(query_in)
        rows = select_in_db.all()
        if len(rows) == 0:
            return batch
        non_exist = []
        for item in items:
            # check if for given item num_splits == num returned rows
            rows_for_item = list(filter(lambda row: row.extras['source_path'] == item[DataSourceBlockMetadata.path.name], rows))
            if len(rows_for_item) == 0:
                non_exist.append(item)
                continue
            # TODO verify split ids?
            num_splits = rows_for_item[0].extras['num_splits']
            if len(rows_for_item) != num_splits:
                non_exist.append(item)

        print(f'Checked db for items: {len(non_exist)} not in DB')
        return meta, non_exist

    # api methods
    def select_data_source_metadata(
        self,
        keys: List[str],
        compaction: Optional[str] = None,
        extras: Optional[str] = None,
        start_day: Optional[str] = None,
        end_day: Optional[str] = None
    ) -> List[Dict]:
        # TODO instrument_extra
        args = {}
        if compaction is not None:
            args[DataSourceBlockMetadata.compaction.name] = compaction
        if extras is not None:
            args[DataSourceBlockMetadata.extras.name] = extras

        session = Session()
        q = session.query(DataSourceBlockMetadata).filter(DataSourceBlockMetadata.key.in_(keys)).filter_by(**args)
        if start_day is not None:
            q = q.filter(DataSourceBlockMetadata.day >= start_day)
        if end_day is not None:
            q = q.filter(DataSourceBlockMetadata.day <= end_day)
        res = q.order_by(DataSourceBlockMetadata.start_ts).all()
        # TODO this adds unnecessary sqlalchemy fields, remove to reduce memory footprint
        return [r.__dict__ for r in res]

    def feature_block_exists(self, item: FeatureBlockMetadata) -> bool:
        session = Session()
        q = session.query(FeatureBlockMetadata).filter(FeatureBlockMetadata.hash == item.hash)
        res = session.query(q.exists()).all()
        if len(res) == 0:
            return False
        return res[0][0]

    def select_feature_blocks_metadata(
        self,
        feature_keys: List[str],
        start_day: Optional[str] = None,
        end_day: Optional[str] = None
    ) -> List[Dict]:
        session = Session()
        f = session.query(FeatureBlockMetadata).filter(FeatureBlockMetadata.key.in_(feature_keys))
        if start_day is not None:
            f = f.filter(FeatureBlockMetadata.day >= start_day)
        if end_day is not None:
            f = f.filter(FeatureBlockMetadata.day <= end_day)
        res = f.order_by(FeatureBlockMetadata.start_ts).all()
        # TODO this adds unnecessary sqlalchemy fields, remove to reduce memory footprint
        return [r.__dict__ for r in res]


    def delete_feature_metadata(
        self,
        feature_keys: List[str]
    ):
        session = Session()
        session.query(FeatureMetadata).filter(FeatureMetadata.key.in_(feature_keys)).delete()
        session.query(FeatureBlockMetadata).filter(FeatureBlockMetadata.key.in_(feature_keys)).delete()
        session.commit()

    def write_feature_def(
        self,
        item: FeatureDefinitionDB
    ):
        session = Session()
        session.add(item)
        session.commit()

    def get_feature_def(
        self,
        owner_id: str,
        feature_group: str,
        feature_definition: str,
        version: str,
    ) -> FeatureDefinitionDB:
        session = Session()
        return session.query(FeatureDefinitionDB).get((owner_id, feature_group, feature_definition, version))
