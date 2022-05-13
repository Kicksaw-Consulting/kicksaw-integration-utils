import boto3
import json

from moto import mock_sqs

from kicksaw_integration_utils.sqs_helpers import (
    get_queue_url,
    pull_n_number_of_messages,
    acknowledge_messages,
)


@mock_sqs
def test_get_queue_url():
    queue_name = "fake-queue"
    sqs = boto3.client("sqs", region_name="us-east-1")
    sqs.create_queue(
        QueueName=queue_name,
        Attributes={
            "DelaySeconds": "0",
            "VisibilityTimeout": "60",
        },
    )

    assert (
        get_queue_url(sqs, queue_name)
        == "https://queue.amazonaws.com/123456789012/fake-queue"
    )


@mock_sqs
def test_pull_n_number_of_messages():
    queue_name = "fake-queue"
    sqs = boto3.client("sqs", region_name="us-east-1")
    sqs.create_queue(
        QueueName=queue_name,
        Attributes={
            "DelaySeconds": "0",
            "VisibilityTimeout": "60",
        },
    )
    queue_url = get_queue_url(sqs, queue_name)

    size = 13

    for i in range(size):
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({"i": i}),
        )

    messages = pull_n_number_of_messages(sqs, queue_name, n=20)

    assert len(messages) == size

    acknowledge_messages(sqs, queue_name, messages)

    messages = pull_n_number_of_messages(sqs, queue_name)

    assert len(messages) == 0
