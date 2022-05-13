from kicksaw_integration_utils.utils import batch_collection


def get_queue_url(sqs_client, queue_name: str):
    return sqs_client.get_queue_url(QueueName=queue_name)["QueueUrl"]


def pull_n_number_of_messages(sqs_client, queue_name: str, n: int = 10000):
    queue_url = get_queue_url(sqs_client, queue_name)
    messages = list()
    while True:
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=0,
            MessageAttributeNames=["All"],
        )
        if not response.get("Messages"):
            break
        else:
            messages += response["Messages"]

        if n <= len(messages):
            break
    return messages


def acknowledge_messages(sqs_client, queue_name: str, messages: list):
    queue_url = get_queue_url(sqs_client, queue_name)
    for batch in batch_collection(messages, 10):
        entries = list()
        for message in batch:
            entries.append(
                {
                    "Id": message["MessageId"],
                    "ReceiptHandle": message["ReceiptHandle"],
                }
            )
        sqs_client.delete_message_batch(QueueUrl=queue_url, Entries=entries)