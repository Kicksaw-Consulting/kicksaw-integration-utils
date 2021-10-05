import json

from types import SimpleNamespace

from kicksaw_integration_utils import SalesforceClient
from kicksaw_integration_utils.integrations.salesforce import KicksawSalesforce

from simple_mockforce import mock_salesforce

import kicksaw_integration_utils.salesforce_client as salesforce_client_module

mock_settings = SimpleNamespace(
    SFDC_USERNAME="mock",
    SFDC_PASSWORD="mock",
    SFDC_SECURITY_TOKEN="mock",
    SFDC_DOMAIN="mock",
)

LAMBDA_NAME = "example-lambda"


@mock_salesforce(fresh=True)
def test_kicksaw_salesforce_client_instantiation(monkeypatch):
    monkeypatch.setattr(salesforce_client_module, "settings", mock_settings)
    _salesforce = SalesforceClient()
    _salesforce.Integration__c.create({"Name": LAMBDA_NAME})
    salesforce = KicksawSalesforce(LAMBDA_NAME, {})

    response = salesforce.query(f"Select Id From {KicksawSalesforce.EXECUTION}")
    assert response["totalSize"] == 1

    records = response["records"]
    record = records[0]

    assert record["Id"] == salesforce.execution_object_id

    # instantiating with an id means we don't create an execution object
    salesforce = KicksawSalesforce(
        LAMBDA_NAME, {}, execution_object_id=salesforce.execution_object_id
    )

    # since we provided an id, the above instantiation should not have created another
    # execution object
    response = salesforce.query(f"Select Id From {KicksawSalesforce.EXECUTION}")
    assert response["totalSize"] == 1

    records = response["records"]
    record = records[0]

    assert record["Id"] == salesforce.execution_object_id


@mock_salesforce(fresh=True)
def test_kicksaw_salesforce_client(monkeypatch):
    monkeypatch.setattr(salesforce_client_module, "settings", mock_settings)

    _salesforce = SalesforceClient()

    integration__c = _salesforce.Integration__c.create({"Name": LAMBDA_NAME})
    integration_id = integration__c["id"]

    step_function_payload = {"start_date": "2021-10-12"}
    salesforce = KicksawSalesforce(LAMBDA_NAME, step_function_payload)

    execution_object = salesforce.get_execution_object()

    assert execution_object[KicksawSalesforce.INTEGRATION] == integration_id
    assert execution_object[KicksawSalesforce.EXECUTION_PAYLOAD] == json.dumps(
        step_function_payload
    )

    data = [
        {"UpsertKey__c": "1a2b3c", "Name": "Name 1"},
        {"UpsertKey__c": "xyz123", "Name": "Name 2"},
        # note, this is a duplicate id, so this and the first row will fail
        {"UpsertKey__c": "1a2b3c", "Name": "Name 1"},
    ]

    response = salesforce.bulk.CustomObject__c.upsert(data, "UpsertKey__c")

    response = salesforce.query(
        f"""
        Select
            {KicksawSalesforce.EXECUTION},
            {KicksawSalesforce.OPERATION}, 
            {KicksawSalesforce.SALESFORCE_OBJECT}, 
            {KicksawSalesforce.ERROR_CODE},
            {KicksawSalesforce.ERROR_MESSAGE}, 
            {KicksawSalesforce.UPSERT_KEY}, 
            {KicksawSalesforce.UPSERT_KEY_VALUE},
            {KicksawSalesforce.OBJECT_PAYLOAD}
        From {KicksawSalesforce.ERROR}
        """
    )
    assert response["totalSize"] == 2
    records = response["records"]

    count = 0
    for record in records:
        assert record[KicksawSalesforce.EXECUTION] == execution_object["Id"]
        assert record[KicksawSalesforce.OPERATION] == "upsert"
        assert record[KicksawSalesforce.SALESFORCE_OBJECT] == "CustomObject__c"
        assert record[KicksawSalesforce.ERROR_CODE] == "DUPLICATE_EXTERNAL_ID"
        assert (
            record[KicksawSalesforce.ERROR_MESSAGE]
            == "A user-specified external ID matches more than one record during an upsert."
        )
        assert record[KicksawSalesforce.UPSERT_KEY] == "UpsertKey__c"
        assert record[KicksawSalesforce.UPSERT_KEY_VALUE] == "1a2b3c"
        assert record[KicksawSalesforce.OBJECT_PAYLOAD] == json.dumps(
            {
                "UpsertKey__c": "1a2b3c",
                "Name": "Name 1",
            }
        )

        count += 1

    assert count == 2
