import boto3
import pytest

from moto import mock_sqs
from pydantic import BaseModel

from kicksaw_integration_utils.aws import SQSQueue


class Message(BaseModel):
    number: int
    message: str


@pytest.fixture(scope="function")
def messages():
    return [Message(number=i, message=f"Message #{i}") for i in range(10)]


@pytest.fixture(scope="function")
def queue():
    with mock_sqs():
        queue_name = "test-queue-name"
        sqs_client = boto3.client("sqs", region_name="us-east-1")
        sqs_client.create_queue(QueueName=queue_name)
        yield SQSQueue.from_name(queue_name, Message, region_name="us-east-1")


def test_multiple_messages(queue: SQSQueue, messages: list[BaseModel]):
    # Send messages
    send_results = queue.send_messages(messages)
    assert all(send_results)

    # Receive messages
    handles, received_messages = queue.receive_messages()
    assert len(handles) == len(received_messages) == len(messages)
    assert all(sent == received for sent, received in zip(messages, received_messages))

    # Delete messages
    delete_results = queue.delete_messages(handles)
    assert all(delete_results)

    # Make sure queue has no more messages
    handles, received_messages = queue.receive_messages()
    assert len(handles) == len(received_messages) == 0


def test_send_single_message(queue: SQSQueue):
    message = Message(number=13, message="hello")
    message_id = queue.send_message(message)
    assert isinstance(message_id, str)

    handles, received_messages = queue.receive_messages()
    assert len(handles) == len(received_messages) == 1
