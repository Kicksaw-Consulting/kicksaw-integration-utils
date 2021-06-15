import boto3

from moto import mock_s3

from kicksaw_integration_utils.step_function_helpers import (
    cache_data_in_s3,
    pull_cached_data_from_s3,
)


@mock_s3
def test_cache_data_in_s3_and_pull_cached_data_from_s3():
    s3 = boto3.client("s3")
    bucket_name = "a-bucket"
    s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )

    data = {"greeting": "hi"}
    s3_key = cache_data_in_s3(data, bucket_name)

    retrieved_data = pull_cached_data_from_s3(bucket_name, s3_key)

    assert retrieved_data == data
