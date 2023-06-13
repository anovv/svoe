import os
from typing import Optional, List, Dict

import requests

from client.base_client import BaseClient


class FeaturizerClient(BaseClient):

    def __init__(self):
        super(FeaturizerClient, self).__init__()

    # https://stackoverflow.com/questions/65504438/how-to-add-both-file-and-json-body-in-a-fastapi-post-request/70640522#70640522
    # https://github.com/openapi-generators/openapi-python-client/blob/main/integration-tests/tests/test_api/test_body/test_post_body_multipart.py
    def register_feature_definition(
        self,
        feature_group: str,
        feature_definition: str,
        version: str,
        local_path: str,
        tags: Optional[List[Dict]] = None
    ) -> bool:
        file_set = set()
        for _dir, _, files in os.walk(local_path):
            for file_name in files:
                rel_dir = os.path.relpath(_dir, local_path)
                if rel_dir != dir:
                    rel_file = os.path.join(rel_dir, file_name)
                else:
                    rel_file = file_name
                file_set.add(rel_file)
        file_names = list(file_set)
        if len(file_names) > 10:
            raise ValueError('Can not upload more than 10 files')

        # generated open-api client code does not work, so use plain requests for now
        # TODO update when issue is fixed
        # https://github.com/openapi-generators/openapi-python-client/issues/771
        files = [('files', open(file_name, 'rb')) for file_name in file_names]
        params = {
            'owner_id': '0', # TODO
            'feature_group': feature_group,
            'feature_definition': feature_definition,
            'version': version
        }
        if tags is not None:
            params['tags'] = tags
        r = requests.post(
            url=f'{self.base_url}/feature_definition/',
            params=params,
            files=files
        )
        print(r.json())
        return r.json()['result']


if __name__ == '__main__':
    client = FeaturizerClient()
    client.register_feature_definition(
        feature_group='test_feature_group',
        feature_definition='test_feature_definition',
        version='1',
        local_path='.'
    )