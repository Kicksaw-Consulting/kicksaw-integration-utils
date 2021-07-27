import csv
import os

from kicksaw_integration_utils.orchestrator import Orchestrator

import kicksaw_integration_utils.orchestrator as orchestrator_module


class MockSfClient:
    def __init__(self, *args, **kwargs) -> None:
        pass


def test_orchestrator(monkeypatch):
    monkeypatch.setattr(
        orchestrator_module, "download_file", lambda *args: "tests/sample.csv"
    )
    monkeypatch.setattr(orchestrator_module, "SfClient", MockSfClient)

    s3_key = "junk.csv"
    bucket = "a bucket"
    orchestrator = Orchestrator(s3_key, bucket)

    data = []
    results = []
    with open(orchestrator.downloaded_file) as csv_file:
        csv_reader = csv.DictReader(csv_file)

        for idx, row in enumerate(csv_reader):
            data.append(row)

            if idx == 0:
                results.append(
                    {
                        "success": False,
                        "created": False,
                        "Id": idx,
                        "errors": [{"statusCode": "DIDNT_WORK", "message": "it broke"}],
                    },
                )
            else:
                results.append(
                    {
                        "success": True,
                        "created": True,
                        "Id": idx,
                        "errors": [],
                    },
                )

    # imagine we pushed to salesforce
    orchestrator.log_batch(results, data, "Contact", "ID")

    with open(orchestrator.error_report_path) as error_report:
        csv_reader = csv.DictReader(error_report)

        count = 0
        for idx, row in enumerate(csv_reader):
            assert row["code"] == "DIDNT_WORK"
            assert row["message"] == "it broke"
            assert row["upsert_key_value"] == "1"
            assert row["upsert_key"] == "ID"
            assert row["salesforce_object"] == "Contact"
            count += 1
        assert count == 1

    # test appending
    data_2 = [{"ID": 4, "Name": "A"}, {"ID": 5, "Name": "B"}, {"ID": 6, "Name": "C"}]
    results_2 = [
        {
            "success": False,
            "created": True,
            "Id": 4,
            "errors": [{"statusCode": "WEIRD_FAIL_1", "message": "it is broken 1"}],
        },
        {
            "success": False,
            "created": True,
            "Id": 5,
            "errors": [{"statusCode": "WEIRD_FAIL_2", "message": "it is broken 2"}],
        },
        {
            "success": False,
            "created": True,
            "Id": 6,
            "errors": [{"statusCode": "WEIRD_FAIL_3", "message": "it is broken 3"}],
        },
    ]
    orchestrator.log_batch(
        results_2,
        data_2,
        "Contact",
        "ID",
    )

    timestamp = orchestrator.get_timestamp()

    with open(orchestrator.error_report_path) as error_report:
        csv_reader = csv.DictReader(error_report)
        count = 0
        for idx, row in enumerate(csv_reader):
            if idx == 0:
                assert row["code"] == "DIDNT_WORK"
                assert row["message"] == "it broke"
                assert row["upsert_key_value"] == "1"
                assert row["upsert_key"] == "ID"
                assert row["salesforce_object"] == "Contact"
            elif idx == 1:
                assert row["code"] == "WEIRD_FAIL_1"
                assert row["message"] == "it is broken 1"
                assert row["upsert_key_value"] == "4"
                assert row["upsert_key"] == "ID"
                assert row["salesforce_object"] == "Contact"
            elif idx == 2:
                assert row["code"] == "WEIRD_FAIL_2"
                assert row["message"] == "it is broken 2"
                assert row["upsert_key_value"] == "5"
                assert row["upsert_key"] == "ID"
                assert row["salesforce_object"] == "Contact"
            elif idx == 3:
                assert row["code"] == "WEIRD_FAIL_3"
                assert row["message"] == "it is broken 3"
                assert row["upsert_key_value"] == "6"
                assert row["upsert_key"] == "ID"
                assert row["salesforce_object"] == "Contact"
            count += 1
        assert count == 4

    assert orchestrator.archive_file_s3_key == f"archive/junk-{timestamp}.csv"
    assert orchestrator.error_file_s3_key == f"errors/error-report-{timestamp}.csv"

    os.remove(orchestrator.error_report_path)
