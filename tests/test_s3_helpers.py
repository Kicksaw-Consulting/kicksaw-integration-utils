import boto3
import os
import pytest

from pathlib import Path

from botocore.exceptions import ClientError

from moto import mock_s3

from kicksaw_integration_utils.utils import get_iso
from kicksaw_integration_utils.s3_helpers import (
    get_prefix_from_s3_key,
    parse_kinesis_record,
    timestamp_s3_key,
    respond_to_s3_event,
    move_file,
    upload_file,
    download_file,
    get_filename_from_s3_key,
    parse_s3_event_record,
    build_archive_s3_key,
)


@pytest.mark.parametrize(
    "delete",
    [
        True,
        False,
    ],
)
@mock_s3
def test_move_file(delete):
    s3_client = boto3.client("s3")
    bucket_name = "a-bucket"
    s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )

    s3_key = "file.csv"

    upload_file(Path("tests") / "sample.csv", bucket_name, s3_key)

    new_key = "better-file.csv"
    move_file(s3_key, new_key, bucket_name, delete=delete)

    download_file(new_key, bucket_name)

    failed = False
    try:
        download_file(s3_key, bucket_name)
    except ClientError:
        failed = True

    if delete:
        assert failed
    else:
        assert not failed


@mock_s3
def test_move_file_to_another_bucket():
    s3_client = boto3.client("s3")
    bucket_name = "a-bucket"
    other_bucket_name = "a-better-bucket"
    s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )
    s3_client.create_bucket(
        Bucket=other_bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )

    s3_key = "file.csv"

    upload_file(Path("tests") / "sample.csv", bucket_name, s3_key)

    new_key = "better-file.csv"
    move_file(s3_key, new_key, bucket_name, new_bucket=other_bucket_name, delete=True)

    download_file(new_key, other_bucket_name)

    failed = False
    try:
        download_file(s3_key, bucket_name)
    except ClientError:
        failed = True

    assert failed


@pytest.mark.parametrize(
    "s3_key,keep_folder,expected",
    [
        ("origin/a_file.csv", False, f"a_file-{get_iso()}.csv"),
        ("origin/a_file.csv", True, os.path.join("origin", f"a_file-{get_iso()}.csv")),
    ],
)
def test_timestamp_s3_key(s3_key, keep_folder, expected):
    timestamped_s3_key = timestamp_s3_key(s3_key, keep_folder)
    assert timestamped_s3_key == expected


@pytest.mark.parametrize(
    "record, expected_bucket, expected_key",
    [
        (
            {
                "s3": {
                    "bucket": {"name": "bucket"},
                    "object": {"key": "origin/a_file.csv"},
                },
            },
            "bucket",
            "origin/a_file.csv",
        ),
        (
            {
                "s3": {
                    "bucket": {"name": "bucket"},
                    "object": {"key": "Im+a+problem.csv"},
                },
            },
            "bucket",
            "Im a problem.csv",
        ),
    ],
)
def test_parse_s3_event_record(record, expected_bucket, expected_key):
    bucket_name, s3_key = parse_s3_event_record(record)
    assert expected_bucket == bucket_name
    assert expected_key == s3_key


@pytest.mark.parametrize(
    "s3_key,expected_s3_key,bucket,expected_bucket",
    [
        ("origin/a_file.csv", "origin/a_file.csv", "bucket", "bucket"),
        (
            "origin/a_%7Bfile%7D.csv",
            r"origin/a_{file}.csv",
            "%7Bbucket%7D",
            r"{bucket}",
        ),
        ("Im+a+problem.csv", "Im a problem.csv", "bucket", "bucket"),
    ],
)
def test_respond_to_s3_event(s3_key, expected_s3_key, bucket, expected_bucket):
    def process(s3_object_key, bucket_name):
        assert s3_object_key == expected_s3_key
        assert bucket_name == expected_bucket

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": s3_key},
                },
            }
        ]
    }
    respond_to_s3_event(event, process)


@pytest.mark.parametrize(
    "record,expected",
    [
        (
            {
                "kinesis": {
                    "data": "eyJOYW1lIjogIkJvYiIsICJVbmlxdWVJZF9fYyI6ICIxMjMifQ==",
                },
            },
            {"Name": "Bob", "UniqueId__c": "123"},
        ),
    ],
)
def test_parse_kinesis_record(record, expected):
    data = parse_kinesis_record(record)
    assert expected == data


@pytest.mark.parametrize(
    "s3_key,expected",
    [
        ("origin/a_file.csv", "a_file.csv"),
        ("another_file.csv", "another_file.csv"),
        ("a/b/c/file.csv", "file.csv"),
    ],
)
def test_get_filename_from_s3_key(s3_key, expected):
    filename = get_filename_from_s3_key(s3_key)
    assert filename == expected


@pytest.mark.parametrize(
    "s3_key,expected",
    [
        ("origin/a_file.csv", "origin"),
        ("a/b/c/file.csv", "a/b/c"),
    ],
)
def test_get_prefix_from_s3_key(s3_key, expected):
    prefix = get_prefix_from_s3_key(s3_key)
    assert prefix == expected


@pytest.mark.parametrize(
    "s3_key,nested_prefix,replace,expected",
    [
        ("origin/a_file.csv", None, True, "archive/a_file.csv"),
        ("a/b/c/file.csv", None, False, "archive/a/b/c/file.csv"),
        ("a/b/c/file.csv", Path("d"), False, "archive/a/b/c/d/file.csv"),
    ],
)
def test_build_archive_s3_key(s3_key, nested_prefix, replace, expected):
    archive_s3_key = build_archive_s3_key(
        s3_key, nested_prefix=nested_prefix, replace=replace
    )
    assert archive_s3_key == expected