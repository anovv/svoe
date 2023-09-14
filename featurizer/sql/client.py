from typing import Optional, Dict, List
from common.db.sql_client import SqlClient, Session
from featurizer.sql.data_catalog.models import DataCatalog
from featurizer.sql.feature_catalog.models import FeatureCatalog
from featurizer.data_catalog.common.data_models.models import InputItemBatch


from featurizer.sql.feature_def.models import FeatureDefinitionDB


class FeaturizerSqlClient(SqlClient):
    def __init__(self, config: Optional[Dict] = None):
        super(FeaturizerSqlClient, self).__init__(config=config)

    # TODO separate api methods and pipeline methods
    def write_catalog_item_batch(self, batch: List[DataCatalog | FeatureCatalog]):
        # TODO figure out insert_or_update logic
        session = Session()
        session.bulk_save_objects(batch)

        # TODO try catch and handle
        # 1) connection issues
        # 2) duplicate entries
        session.commit()
        print(f'Written {len(batch)} index items to Db')
        return # TODO return result?


    def filter_cryptofeed_batch(self, batch: InputItemBatch) -> InputItemBatch:
        # use path as a unique id per block
        items = batch[1]
        meta = batch[0]
        paths = [item[DataCatalog.path.name] for item in items]
        query_in = DataCatalog.path.in_(paths)
        session = Session()
        select_in_db = session.query(DataCatalog.path).filter(query_in)
        res = [r[0] for r in select_in_db.all()]
        non_exist = list(filter(lambda item: item[DataCatalog.path.name] not in res, items))
        print(f'Checked db for items: {len(non_exist)} not in DB')
        return meta, non_exist


    def filter_cryptotick_batch(self, batch: InputItemBatch) -> InputItemBatch:
        items = batch[1]
        meta = batch[0]
        paths = [item[DataCatalog.path.name] for item in items]
        session = Session()
        query_in = DataCatalog.extras['source_path'].in_(paths)
        select_in_db = session.query(DataCatalog).filter(query_in)
        rows = select_in_db.all()
        if len(rows) == 0:
            return batch
        non_exist = []
        for item in items:
            # check if for given item num_splits == num returned rows
            rows_for_item = list(filter(lambda row: row.extras['source_path'] == item[DataCatalog.path.name], rows))
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
    def select_data_catalog(
        self,
        exchanges: List[str],
        data_types: List[str],
        instrument_types: List[str],
        symbols: List[str],
        instrument_extra: Optional[str] = None,
        compaction: Optional[str] = None,
        source: Optional[str] = None,
        version: Optional[str] = None,
        extras: Optional[str] = None,
        start_day: Optional[str] = None,
        end_day: Optional[str] = None
    ) -> List[Dict]:
        # TODO instrument_extra
        args = {}
        if compaction is not None:
            args[DataCatalog.compaction.name] = compaction
        if source is not None:
            args[DataCatalog.symbol.name] = source
        if version is not None:
            args[DataCatalog.version.name] = version
        if extras is not None:
            args[DataCatalog.extras.name] = extras

        session = Session()
        q = session.query(DataCatalog).filter(DataCatalog.exchange.in_(exchanges))\
            .filter(DataCatalog.data_type.in_(data_types))\
            .filter(DataCatalog.instrument_type.in_(instrument_types))\
            .filter(DataCatalog.symbol.in_(symbols))\
            .filter_by(**args)
        if start_day is not None:
            q = q.filter(DataCatalog.date >= start_day)
        if end_day is not None:
            q = q.filter(DataCatalog.date <= end_day)
        res = q.order_by(DataCatalog.start_ts).all()
        # TODO this adds unnecessary sqlalchemy fields, remove to reduce memory footprint
        return [r.__dict__ for r in res]

    def in_feature_catalog(self, item: FeatureCatalog) -> bool:
        session = Session()
        q = session.query(FeatureCatalog).filter(FeatureCatalog.hash == item.hash)
        res = session.query(q.exists()).all()
        if len(res) == 0:
            return False
        return res[0][0]

    def select_feature_catalog(
        self,
        feature_keys: List[str],
        start_day: Optional[str] = None,
        end_day: Optional[str] = None
    ) -> List[Dict]:
        session = Session()
        f = session.query(FeatureCatalog).filter(FeatureCatalog.feature_key.in_(feature_keys))
        if start_day is not None:
            f = f.filter(FeatureCatalog.date >= start_day)
        if end_day is not None:
            f = f.filter(FeatureCatalog.date <= end_day)
        res = f.order_by(FeatureCatalog.start_ts).all()
        # TODO this adds unnecessary sqlalchemy fields, remove to reduce memory footprint
        return [r.__dict__ for r in res]

    def delete_feature_catalog(
        self,
        feature_keys: List[str]
    ):
        session = Session()
        session.query(FeatureCatalog).filter(FeatureCatalog.feature_key.in_(feature_keys)).delete()
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
