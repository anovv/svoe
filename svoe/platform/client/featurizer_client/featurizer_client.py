import io
import os
import zipfile
from typing import Optional, List, Dict

import requests

from svoe.platform.client.base_client import BaseClient


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
        for file in os.listdir(local_path):
            if file == '__pycache__':
                continue
            if not os.path.isfile(os.path.join(local_path, file)):
                print(file)
                raise ValueError('Feature definition dir should contain only files')
            file_set.add(os.path.join(local_path, file))

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

    def load_feature_definition(
        self,
        feature_group: str,
        feature_definition: str,
        version: str,
        extract_path: str,
    ) -> Optional[str]:
        # TODO generated OpenAPI cli is not able to parse bytes properly, hence we use raw requests
        resp = requests.get(f'{self.base_url}/feature_definition/', params={
            'owner_id': '0', # TODO
            'feature_group': feature_group,
            'feature_definition': feature_definition,
            'version': version
        })
        try:
            # if we can convert to json then endpoint returned dict obj, which means it an error
            res = resp.json()
            err = res['err']
            print(f'Error loading feature definition: {err}')
            return None
        except Exception as e:
            pass

        # response is array of bytes
        z = zipfile.ZipFile(io.BytesIO(resp.content))
        z.extractall(path=extract_path)
        return extract_path



if __name__ == '__main__':
    client = FeaturizerClient()
    client.register_feature_definition(
        feature_group='tvi',
        feature_definition='trade_volume_imb_fd',
        version='1',
        local_path='/featurizer/features/definitions/tvi/'
    )
    # client.load_feature_definition(
    #     feature_group='test_feature_group',
    #     feature_definition='test_feature_definition',
    #     version='1',
    #     extract_path='./dd'
    # )