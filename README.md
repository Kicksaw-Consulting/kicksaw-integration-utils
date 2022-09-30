- [API Reference](#api-reference)
  - [AWS](#aws)
    - [SQS](#sqs)
- [Overview](#overview)
- [High-level Example](#high-level-example)
  - [Inheriting the Orchestrator](#inheriting-the-orchestrator)
  - [Using the Orchestrator](#using-the-orchestrator)
- [Low-level Example](#low-level-example)

# API Reference

## AWS

Helper classes and functions to interact with and manipulate AWS services.

### SQS

Make sure to provide type hint `SQSQueue[Patient]` to enable type hints for the queue
methods.

Send messages:

```python
from kicksaw_integration_utils.aws import SQSQueue
from pydantic import BaseModel


class Patient(BaseModel):
    first_name: str
    last_name: str
    age: int


messages = [
    Patient(first_name="John", last_name="Doe", age=40),
    Patient(first_name="Jane", last_name="Doe", age=30),
]


queue: SQSQueue[Patient] = SQSQueue(name="my-queue-name", message_model=Patient)
queue.send_messages(messages)
```

Receive and delete messages:

```python
handles, messages = queue.receive_messages()
queue.delete_messages(handles)
```

# Overview

A set of helper functions for CSV to Salesforce procedures, with reporting in AWS S3.
The use case is extremely specific, but the helpers should be modular so they can be cherry-picked.

Typical use case:

- Receive an S3 event
- Download the S3 object
- Serialize the file into JSON
- Bulk upsert the JSON data to Salesforce
- Parse the results of the upsert for errors
- Construct a CSV error report
- Move the triggering S3 object to an archive folder
- Push the error report to an error folder in the same bucket
- Push an object to Salesforce that details information about the above execution

2nd typical use case:

- Start an AWS Step Function
- Pass the payload to the KicksawSalesforce client and create an execution object, recording this payload
- upsert a bunch of data, parsing the responses
- if any errors, push error objects into salesforce, chidling them to the execution object above

# High-level Example

Using the `Orchestrator` class, you can skip manually setting up a lot of the above
steps. This class is intended to be subclassed, and should provide plenty of options
for overriding methods to better suit your use-case.

## Inheriting the Orchestrator

```python
# orchestrator.py
from kicksaw_integration_utils.classes import Orchestrator as BaseOrchestrator


class Orchestrator(BaseOrchestrator):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # This must be defined in the child class because your Salesforce object could be named anything
        self.execution_object_name = "Integration_Execution__c"

    @property
    def execution_sfdc_hash(self):
        # And it could have any number of fields
        return {
            "Number_of_Errors__c": self.error_count,
            "Error_Report__c": self.error_report_link,
            "Data_File__c": self.s3_object_key,
        }

    @property
    def error_report_link(self):
        return f"https://{self.bucket_name}.{config.AWS_REGION}.amazonaws.com/{self.error_file_s3_key}"
```

## Using the Orchestrator

```python
# biz_logic.py
from kicksaw_integration_utils.classes import SfClient

# import the custom Orchestrator defined above
from .orchestrator import Orchestrator

salesforce = SfClient()
orchestrator = Orchestrator("some/s3/key/file.csv", config.S3_BUCKET, sf_client=salesforce)

upsert_key = "My_External_ID__c"
accounts_data = [{"Name": "A name", upsert_key: "123"}]
results = salesforce.bulk.Account.upsert(results, upsert_key)

# You'll call log_batch for each batch you upload. This method
# will parse the results in search of errors
orchestrator.log_batch(results, accounts_data, "Account", upsert_key)

# This will create the error report, archive the source s3 file, and push
# the integration object to Salesforce. You'll definitely want to customize
# this by overriding this method or the methods it invokes
orchestrator.automagically_finish_up()
```

# Low-level Example

```python
from kicksaw_integration_utils.csv_helpers import create_error_report
from kicksaw_integration_utils.s3_helpers import download_file, respond_to_s3_event, upload_file
from kicksaw_integration_utils.sfdc_helpers import extract_errors_from_results


# handler for listening to s3 events
def handler(event, context):
    respond_to_s3_event(event, download_and_process)


def download_and_process(s3_object_key, bucket_name):
    download_path = download_file(s3_object_key, bucket_name)

    # This function contains your own biz logic; does not come from this library
    results = serialize_and_push_to_sfdc(download_path)

    sucesses, errors = parse_bulk_upsert_results(results)

    report_path, errors_count = create_error_report([errors])

    upload_file(report_path, bucket_name)
```

Just take what'cha need!
