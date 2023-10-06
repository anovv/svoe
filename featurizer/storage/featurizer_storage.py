import os
import tempfile
import zipfile
from io import BytesIO

from fastapi import UploadFile
from portion import Interval, closed

from typing import Optional, Dict, List, Tuple

from common.time.utils import date_str_to_day_str, date_str_to_ts, round_float
from featurizer.blocks.blocks import BlockRangeMeta, make_ranges, BlockMeta
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.sql.client import FeaturizerSqlClient
from featurizer.sql.feature_def.models import construct_feature_def_s3_path, FeatureDefinitionDB
from common.s3.s3_utils import delete_files, upload_dir, download_dir
from featurizer.sql.models.data_source_block_metadata import DataSourceBlockMetadata
from featurizer.sql.models.feature_block_metadata import FeatureBlockMetadata
from featurizer.sql.models.feature_metadata import FeatureMetadata
from featurizer.storage.data_store_adapter.remote_data_store_adapter import SVOE_S3_FEATURE_CATALOG_BUCKET


class FeaturizerStorage:
    def __init__(self):
        self.client = FeaturizerSqlClient()

    def get_data_sources_meta(
        self,
        features: List[Feature],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[Feature, List[BlockRangeMeta]]:
        data_deps = set()
        synthetic_data_deps = set()
        for feature in features:
            for d in feature.get_data_sources():
                # skip synthetic data sources
                if d.data_definition.is_synthetic():
                    synthetic_data_deps.add(d)
                else:
                    data_deps.add(d)

        data_keys = [d.key for d in data_deps]
        ranges_meta_per_data_key = self._get_data_sources_meta(data_keys, start_date=start_date, end_date=end_date)
        if len(data_deps) != 0 and len(ranges_meta_per_data_key) == 0: # TODO raise only for non-synthetic data
            raise ValueError('No data for given time range')
        res = {data: ranges_meta_per_data_key[data.key] for data in data_deps}

        # add synthetic ranges
        # TODO if start_date or end_date were passed as None we need to derive them from what was returned from database
        for synthetic_data in synthetic_data_deps:
            num_splits = synthetic_data.params.get('num_splits', 1)
            res[synthetic_data] = synthetic_data.data_definition.gen_synthetic_ranges_meta(start_date, end_date, num_splits)

        return res

    def _get_data_sources_meta(
        self,
        keys: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, List[BlockRangeMeta]]:
        start_day = None if start_date is None else date_str_to_day_str(start_date)
        end_day = None if end_date is None else date_str_to_day_str(end_date)
        raw_data = self.client.select_data_source_metadata(keys, start_day=start_day, end_day=end_day)

        start_ts = None if start_date is None else date_str_to_ts(start_date)
        end_ts = None if end_date is None else date_str_to_ts(end_date)
        # group data by key
        groups = {}
        for r in raw_data:
            # filter not in range
            _start_ts = float(r[DataSourceBlockMetadata.start_ts.name])
            _end_ts = float(r[DataSourceBlockMetadata.end_ts.name])
            if start_ts is not None and _end_ts < start_ts:
                continue
            if end_ts is not None and _start_ts > end_ts:
                continue

            key = r['key']

            # TODO we neeed to properly convert raw dict db record to BlockMeta object
            # hacky fix for float precision
            r['start_ts'] = str(round_float(float(r['start_ts'])))
            r['end_ts'] = str(round_float(float(r['end_ts'])))

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

    def store_features_metadata_if_needed(self, features: List[Feature]):
        features_metadata_items = [FeatureMetadata(
            owner_id='0',  # TODO
            key=feature.key,
            feature_definition=feature.data_definition.__name__,
            feature_name=feature.name,
            params=feature.params,
        ) for feature in features]
        self.client.store_metadata_if_needed(features_metadata_items)

    def get_features_meta(
        self,
        features: List[Feature],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[Feature, Dict[Interval, BlockMeta]]: # TODO return FeatureCatalog instead of Dict?
        start_day = None if start_date is None else date_str_to_day_str(start_date)
        end_day = None if end_date is None else date_str_to_day_str(end_date)
        feature_keys = [f.key for f in features]
        raw_data = self.client.select_feature_blocks_metadata(feature_keys, start_day=start_day, end_day=end_day)

        groups = {}
        def _feature_by_key(key):
            for f in features:
                if f.key == key:
                    return f
            return None

        start_ts = None if start_date is None else date_str_to_ts(start_date)
        end_ts = None if end_date is None else date_str_to_ts(end_date)
        for r in raw_data:
            # filter not in range
            feature_key = r[FeatureBlockMetadata.key.name]
            _start_ts = float(r[FeatureBlockMetadata.start_ts.name])
            _end_ts = float(r[FeatureBlockMetadata.end_ts.name])
            if start_ts is not None and _end_ts < start_ts:
                continue
            if end_ts is not None and _start_ts > end_ts:
                continue

            # hacky fix for float precision
            interval = closed(round_float(_start_ts), round_float(_end_ts))
            feature = _feature_by_key(feature_key)
            if feature in groups:
                if interval in groups[feature]:
                    raise ValueError('FeatureBlockMetadata entry duplicate interval')
                groups[feature][interval] = r
            else:
                groups[feature] = {interval: r}

        return groups

    # TODO verify consistency + retries in case of failures
    # TODO delete should also depend on data adapter?
    def delete_features(self, features: List[Feature]):
        feature_keys = [f.key for f in features]
        raw_data = self.client.select_feature_blocks_metadata(feature_keys)
        paths = [r['path'] for r in raw_data]
        delete_files(SVOE_S3_FEATURE_CATALOG_BUCKET, paths)
        self.client.delete_feature_metadata(feature_keys)

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
