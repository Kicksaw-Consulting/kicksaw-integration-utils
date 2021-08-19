import json

from kicksaw_integration_utils.salesforce_client import (
    SfClient,
    SFBulkHandler as BaseSFBulkHandler,
    SFBulkType as BaseSFBulkType,
)


class SFBulkType(BaseSFBulkType):
    def _bulk_operation(self, operation, data, external_id_field=None, **kwargs):
        response = super()._bulk_operation(
            operation, data, external_id_field=external_id_field, **kwargs
        )
        self._process_errors(data, response, operation, external_id_field)
        return response

    def _process_errors(self, data, response, operation, external_id_field):
        """
        Parse the results of a bulk upload call and push error objects into Salesforce
        """
        object_name = self.object_name
        upsert_key = external_id_field

        assert len(data) == len(
            response
        ), f"{len(data)} (data) and {len(response)} (response) have different lengths!"
        assert (
            KicksawSalesforce.execution_object_id
        ), f"KicksawSalesforce.execution_object_id is not set"

        error_objects = list()
        for payload, record in zip(data, response):
            if not record["success"]:
                for error in record["errors"]:
                    error_object = {
                        KicksawSalesforce.EXECUTION: KicksawSalesforce.execution_object_id,
                        KicksawSalesforce.OPERATION: operation,
                        KicksawSalesforce.SALESFORCE_OBJECT: object_name,
                        KicksawSalesforce.ERROR_CODE: error["statusCode"],
                        KicksawSalesforce.ERROR_MESSAGE: error["message"],
                        KicksawSalesforce.UPSERT_KEY: upsert_key,
                        KicksawSalesforce.UPSERT_KEY_VALUE: payload[upsert_key],
                        KicksawSalesforce.OBJECT_PAYLOAD: json.dumps(payload),
                    }
                    error_objects.append(error_object)

        # Push error details to Salesforce
        error_client = BaseSFBulkType(
            KicksawSalesforce.ERROR, self.bulk_url, self.headers, self.session
        )
        error_client.insert(error_objects)


class SFBulkHandler(BaseSFBulkHandler):
    def __getattr__(self, name):
        """
        Source code from this library's SFBulkType
        """
        return SFBulkType(
            object_name=name,
            bulk_url=self.bulk_url,
            headers=self.headers,
            session=self.session,
        )


class KicksawSalesforce(SfClient):
    """
    Salesforce client to use when the integration is using
    the "Integration App" (our Salesforce package for integrations)

    This combines the simple-salesforce client and the
    Orchestrator client from this library
    """

    execution_object_id = None

    # Integration execution object stuff
    EXECUTION = "IntegrationExecution__c"
    EXECUTION_PAYLOAD = "ExecutionPayload__c"  # json input for step function

    # Integration error object stuff
    ERROR = "IntegrationError__c"
    OPERATION = "Operation__c"
    SALESFORCE_OBJECT = "Object__c"
    ERROR_CODE = "ErrorCode__c"
    ERROR_MESSAGE = "ErrorMessage__c"
    UPSERT_KEY = "UpsertKey__c"
    UPSERT_KEY_VALUE = "UpsertKeyValue__c"
    OBJECT_PAYLOAD = "ObjectPayload__c"

    def __init__(self, payload, execution_object_id: str = None):
        """
        In addition to instantiating the simple-salesforce client,
        we also decide whether or not to create an execution object
        based on whether or not we've provided an id for this execution
        """
        self._execution_payload = payload
        super().__init__()
        self._prepare_execution(execution_object_id)

    def _prepare_execution(self, execution_object_id):
        if not execution_object_id:
            execution_object_id = self._create_execution_object()
        KicksawSalesforce.execution_object_id = execution_object_id

    def _create_execution_object(self):
        """
        Pushes an execution object to Salesforce, returning the
        Salesforce id of the object we just created

        Adds the payload for the first step of the step function
        as a field on the execution object
        """
        execution = {
            KicksawSalesforce.EXECUTION_PAYLOAD: json.dumps(self._execution_payload)
        }
        response = getattr(self, KicksawSalesforce.EXECUTION).create(execution)
        return response["id"]

    def get_execution_object(self):
        return getattr(self, KicksawSalesforce.EXECUTION).get(self.execution_object_id)

    def __getattr__(self, name):
        """
        This is the source code from simple salesforce, but we swap out
        SFBulkHandler with our own
        """
        if name == "bulk":
            # Deal with bulk API functions
            return SFBulkHandler(
                self.session_id, self.bulk_url, self.proxies, self.session
            )
        return super().__getattr__(name)
