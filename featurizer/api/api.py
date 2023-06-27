import os
import tempfile
import zipfile
from io import BytesIO

from fastapi import UploadFile
from portion import Interval, closed

from typing import Optional, Dict, List, Tuple

from featurizer.blocks.blocks import BlockRangeMeta, make_ranges, BlockMeta
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.sql.client import MysqlClient
from featurizer.sql.data_catalog.models import DataCatalog
from featurizer.sql.feature_catalog.models import FeatureCatalog, SVOE_S3_FEATURE_CATALOG_BUCKET
from featurizer.sql.feature_def.models import construct_feature_def_s3_path, FeatureDefinitionDB
from utils.s3.s3_utils import delete_files, upload_dir, download_dir

# TODO this should be synced with DataDef somehow?
DataKey = Tuple[str, str, str, str]


def data_key(e: Dict) -> DataKey:
    return (e[DataCatalog.exchange.name], e[DataCatalog.data_type.name], e[DataCatalog.instrument_type.name],
            e[DataCatalog.symbol.name])


# TODO rename to Db
class Api:
    def __init__(self, db_config: Optional[Dict] = None):
        self.client = MysqlClient(db_config)

    def get_data_meta(
        self,
        data_keys: List[DataKey], # TODO make it Feature objects and derive keys
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[DataKey, List[BlockRangeMeta]]:
        exchanges = list(set([d[0] for d in data_keys]))
        data_types = list(set([d[1] for d in data_keys]))
        instrument_types = list(set([d[2] for d in data_keys]))
        symbols = list(set([d[3] for d in data_keys]))
        return self._get_data_meta(exchanges, data_types, instrument_types, symbols, start_date=start_date, end_date=end_date)

    def _get_data_meta(
        self,
        exchanges: List[str],
        data_types: List[str],
        instrument_types: List[str],
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[DataKey, List[BlockRangeMeta]]:
        raw_data = self.client.select_data_catalog(exchanges, data_types, instrument_types, symbols, start_date=start_date, end_date=end_date)
        raw_data = raw_data[:5] # TODO this is for debug
        # group data by data key
        groups = {}
        for r in raw_data:
            key = data_key(r)
            if key in groups:
                groups[key].append(r)
            else:
                groups[key] = [r]

        # make overlaps
        grouped_ranges = {}
        for k in groups:
            ranges = make_ranges(groups[k])
            grouped_ranges[k] = ranges
        return grouped_ranges

    def get_features_meta(
        self,
        features: List[Feature],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[Feature, Dict[Interval, BlockMeta]]: # TODO return FeatureCatalog instead of Dict?
        feature_keys = [f.feature_key for f in features]
        raw_data = self.client.select_feature_catalog(feature_keys, start_date=start_date, end_date=end_date)
        groups = {}

        def _feature_by_key(key):
            for f in features:
                if f.feature_key == key:
                    return f
            return None

        for r in raw_data:
            feature_key = r[FeatureCatalog.feature_key.name]
            start_ts = float(r[FeatureCatalog.start_ts.name])
            end_ts = float(r[FeatureCatalog.end_ts.name])
            interval = closed(start_ts, end_ts)
            feature = _feature_by_key(feature_key)
            if feature in groups:
                if interval in groups[feature]:
                    raise ValueError('FeatureCatalog entry duplicate interval')
                groups[feature][interval] = r
            else:
                groups[feature] = {interval: r}

        return groups

    # TODO verify consistency + retries in case of failures
    def delete_features(self, features: List[Feature]):
        feature_keys = [f.feature_key for f in features]
        raw_data = self.client.select_feature_catalog(feature_keys)
        paths = [r['path'] for r in raw_data]
        delete_files(SVOE_S3_FEATURE_CATALOG_BUCKET, paths)
        self.client.delete_feature_catalog(feature_keys)

    # TODO verify consistency + retries in case of failures
    def store_feature_def(
        self,
        owner_id: str,
        feature_group: str,
        feature_definition: str,
        version: str,
        tags: Optional[List[Dict]],
        files: List[UploadFile]
    ) -> Tuple[bool, Optional[str]]:
        if len(files) == 0:
            return False, 'No files are received'
        # TODO do wee need to set hash?
        item = FeatureDefinitionDB(
            owner_id=owner_id,
            feature_group=feature_group,
            feature_definition=feature_definition,
            version=version,
            tags=tags
        )
        s3_path = construct_feature_def_s3_path(item)
        item.path = s3_path
        temp_dir = None
        # TODO first check if feature def exists, clean up s3 if it does

        try:
            temp_dir = tempfile.TemporaryDirectory()
            for file in files:
                # TODO file.filename does not include subdirs
                # TODO verify file size/content/number of files
                # TODO asyncify
                file_path = f'{temp_dir.name}/{file.filename}'
                with open(file_path, 'wb') as out_file:
                    while content := file.file.read(1024 * 1024):
                        out_file.write(content)

            # upload to s3
            upload_dir(s3_path=s3_path, local_path=f'{temp_dir.name}/')

            # TODO update DB only on S3 success
            self.client.create_tables()
            self.client.write_feature_def(item)
            return True, None
        except Exception as e:
            return False, f'Failed to store feature def: {e}'
        finally:
            if temp_dir:
                temp_dir.cleanup()

    def get_feature_def_files_zipped(
        self,
        owner_id: str,
        feature_group: str,
        feature_definition: str,
        version: str
    ) -> Tuple[Optional[bytes], Optional[str]]:
        temp_dir = None
        try:
            fd_db = self.client.get_feature_def(
                owner_id=owner_id,
                feature_group=feature_group,
                feature_definition=feature_definition,
                version=version
            )
            if not fd_db:
                return None, 'Unable to find feature def in DB'
            s3_path = fd_db.path
            temp_dir, local_files = download_dir(s3_path)

            buf = BytesIO()
            zf = zipfile.ZipFile(buf, "w")
            for fpath in local_files:
                fdir, fname = os.path.split(fpath)
                zf.write(fpath, fname)

            zf.close()
            return buf.getvalue(), None

        except Exception as e:
            return None, f'Failed to get feature def: {e}'
        finally:
            if temp_dir:
                temp_dir.cleanup()
