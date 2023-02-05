from typing import List, Any
from utils.s3 import s3_utils


def list_files(bucket_name: str) -> List[Any]:
    return s3_utils.list_files(bucket_name)


