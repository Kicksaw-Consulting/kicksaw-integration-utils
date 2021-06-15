import csv
from pathlib import Path

from tempfile import gettempdir

from kicksaw_integration_utils.orchestrator import Orchestrator
from kicksaw_integration_utils.utils import get_iso

import kicksaw_integration_utils.orchestrator as orchestrator_module
import kicksaw_integration_utils.csv_helpers as csv_helpers_module


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

    timestamp = get_iso()
    orchestrator.set_timestamp(timestamp)
    orchestrator.generate_error_report()

    with open(orchestrator.error_report_path) as error_report:
        csv_reader = csv.DictReader(error_report)

        for idx, row in enumerate(csv_reader):
            # assert not row
            assert row["code"] == "DIDNT_WORK"
            assert row["message"] == "it broke"
            assert row["upsert_key_value"] == "1"
            assert row["upsert_key"] == "ID"
            assert row["salesforce_object"] == "Contact"

    assert orchestrator.archive_file_s3_key == f"archive/junk-{timestamp}.csv"
    assert orchestrator.error_file_s3_key == f"errors/error-report-{timestamp}.csv"
