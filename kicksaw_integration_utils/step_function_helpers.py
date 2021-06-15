import boto3
import json

from pathlib import Path

from typing import Union

from kicksaw_integration_utils.utils import get_iso

CACHED_DATA = Union[list, dict]


def cache_data_in_s3(data: CACHED_DATA, bucket: str, s3_key: Union[Path, str] = None):
    """
    Caches data in a json file in s3

    Useful when using step functions where payload size is a limit
    """
    s3 = boto3.client("s3")

    if not s3_key:
        iso_stamp = get_iso()
        s3_key = f"data-{iso_stamp}.json"

    s3_key = str(s3_key)

    s3.put_object(Body=json.dumps(data), Bucket=bucket, Key=s3_key)

    return s3_key


def pull_cached_data_from_s3(bucket: str, s3_key: str, delete: bool = False):
    """
    Pulls cached data from a json file in s3

    You can pass delete = True to clean-up the file, but it may be
    safer to delete explicitly once the step is done and the data
    has been been processed
    """
    s3 = boto3.resource("s3")
    s3_object = s3.Object(bucket, s3_key)

    file_content = s3_object.get()["Body"].read().decode("utf-8")
    data: CACHED_DATA = json.loads(file_content)

    if delete:
        s3.delete_object(Bucket=bucket, Key=s3_key)

    return data
