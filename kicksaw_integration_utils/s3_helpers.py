import base64
import boto3
import datetime
import json
import os

from pathlib import Path
from tempfile import gettempdir
from typing import Union
from urllib.parse import unquote_plus

from kicksaw_integration_utils.utils import get_iso


def upload_file(
    local_path: Path,
    bucket: str,
    s3_key: Union[Path, str] = None,
    public_read: bool = False,
) -> str:
    """Upload a file to an S3 bucket

    :param local_path: File to upload
    :param bucket: S3 Bucket to upload to
    :param s3_key: S3 object name. If not specified then local_path is used
    :param public_read: permissions
    """

    # If S3 s3_key was not specified, use local_path
    if s3_key is None:
        s3_key = local_path

    # S3 uses posix-like paths
    if type(s3_key) != str:
        s3_key = s3_key.as_posix()
    # cast to string to get local filesystem's path
    local_path = str(local_path)
    s3_key = str(s3_key)

    s3_client = boto3.client("s3")
    if public_read:
        s3_client.upload_file(
            local_path, bucket, s3_key, ExtraArgs={"ACL": "public-read"}
        )
    else:
        s3_client.upload_file(local_path, bucket, s3_key)

    return s3_key


def move_file(
    old_key: str, new_key: str, bucket: str, new_bucket: str = None, delete: bool = True
):
    """
    Move a file within an S3 bucket by copying to a different path and delete the original
    """
    s3_client = boto3.client("s3")
    copy_source = {"Bucket": bucket, "Key": old_key}
    destination_bucket = new_bucket if new_bucket else bucket
    s3_client.copy(copy_source, destination_bucket, new_key)
    if delete:
        delete_file(old_key, bucket)


def delete_file(s3_key: str, bucket: str):
    s3_client = boto3.client("s3")
    s3_client.delete_object(Bucket=bucket, Key=s3_key)


def download_file(
    s3_object_key: str, bucket_name: str, download_path: Path = None
) -> Path:
    """
    Downloads a file from s3, dropping it in the temp directory
    following the pathing convention from the s3_object_key

        e.g., s3_object_key = archive/a_file.txt
        will drop it in

        %TEMP%/archive/a_file.txt
    """
    if not download_path:
        download_path = Path(os.getenv("TEMP", gettempdir()))

    s3_client = boto3.client("s3")
    download_folder = download_path / os.path.dirname(s3_object_key)
    download_path = download_path / s3_object_key
    # spawn the nested folders without the os complaining
    Path(download_folder).mkdir(parents=True, exist_ok=True)
    s3_client.download_file(bucket_name, s3_object_key, str(download_path))

    return download_path


def timestamp_s3_key(
    s3_key: str, keep_folder: bool = False, timestamp: str = None
) -> str:
    dir_name = os.path.dirname(s3_key)
    file_name = os.path.basename(s3_key)
    name_and_extension = os.path.splitext(file_name)
    assert len(name_and_extension) == 2
    name = name_and_extension[0]
    extension = name_and_extension[1]

    if not timestamp:
        iso = get_iso()
    else:
        iso = timestamp

    timestamped_s3_key = f"{name}-{iso}{extension}"
    if keep_folder:
        return os.path.join(dir_name, timestamped_s3_key)
    return timestamped_s3_key


def parse_s3_event_record(record: dict):
    """
    Returns the bucket name and s3 key associated with an s3 event record
    """
    s3_data = record["s3"]
    bucket = s3_data["bucket"]
    bucket_name = unquote_plus(bucket["name"])
    s3_object = s3_data["object"]
    s3_object_key = unquote_plus(s3_object["key"])
    return bucket_name, s3_object_key


def respond_to_s3_event(event, callback, *args, **kwargs):
    """
    Use like this:
        def process_s3_event(s3_object_key, bucket_name):
            print(s3_object_key, bucket_name)

        def handler(event, context):
            respond_to_s3_event(event, process_s3_event)
    """
    records = event["Records"]
    for record in records:
        bucket_name, s3_object_key = parse_s3_event_record(record)
        callback(s3_object_key, bucket_name, *args, **kwargs)


def parse_kinesis_record(record: dict):
    """
    Returns the decoded data from the kinesis record
    """
    decoded_data = base64.b64decode(record["kinesis"]["data"]).decode("utf-8")
    data = json.loads(decoded_data)
    return data


def get_filename_from_s3_key(s3_key: str):
    return os.path.basename(s3_key)


def get_prefix_from_s3_key(s3_key: str):
    return os.path.dirname(s3_key)


def build_archive_s3_key(
    s3_key: str, nested_prefix: Path = None, replace: bool = False
):
    """
    Given a key, build an archive key

    When replace is True, that means we want to replace the prefix with the word "archive"
    When False, we want to prepend the word "archive"
    """
    s3_key_prefix = get_prefix_from_s3_key(s3_key)
    s3_key_filename = get_filename_from_s3_key(s3_key)

    parts = s3_key_prefix.split("/")
    if replace:
        parts = ["archive"]
    else:
        parts.insert(0, "archive")
    archive_prefix = "/".join(parts)

    if not nested_prefix:
        archive_path = Path(archive_prefix) / s3_key_filename
    else:
        archive_path = Path(archive_prefix) / nested_prefix / s3_key_filename

    return archive_path.as_posix()


def build_date_divided_s3_prefix(date: datetime.date) -> Path:
    """
    Builds and s3 prefix with the given date where each element of the date is an individual prefix

    e.g., 2022-07-05 -> 2022/07/05 (as Path object)
    """
    year = str(date.year)
    if date.month < 10:
        month = f"0{date.month}"
    else:
        month = str(date.month)
    if date.day < 10:
        day = f"0{date.day}"
    else:
        day = str(date.day)
    return Path(year) / month / day