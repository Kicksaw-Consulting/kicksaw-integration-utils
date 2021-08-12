from pathlib import Path

from kicksaw_integration_utils.csv_helpers import create_error_report
from kicksaw_integration_utils.s3_helpers import (
    download_file,
    upload_file,
    timestamp_s3_key,
    move_file,
)
from kicksaw_integration_utils.salesforce_client import SfClient
from kicksaw_integration_utils import settings
from kicksaw_integration_utils.sfdc_helpers import parse_bulk_upsert_results
from kicksaw_integration_utils.utils import get_iso


class Orchestrator:
    """
    This class can be used to orchestrate the following flow

    __init__
    1. S3 event triggerred
    2. File is downloaded

    (developer must implement this code themselves)
    3. File is serialized into whatever the business requirements are (abstract step)
    4. serialized data is pushed to Salesforce (abstract step)
        developer calls log_batch after every push

    automagically_finish_up
    5. results of the push are parsed for errors
    6. an error report csv is created
    7. an archive of the original file and error report are pushed to S3
    8. a custom SFDC object is created, logging all of the above

    If you don't need/need to change something, subclass it!
    """

    def __init__(
        self,
        s3_object_key,
        bucket_name,
        sf_client: SfClient = None,
        archive_folder: str = None,
        error_report_file_name: str = None,
        error_folder: str = None,
        execution_object_name: str = None,
    ) -> None:
        self.s3_object_key = s3_object_key
        self.bucket_name = bucket_name

        self.archive_folder = archive_folder
        self.error_folder = error_folder if error_folder else "errors"

        self.execution_object_name = execution_object_name

        self.download_s3_file()
        self.sf_client = sf_client
        self.timestamp = None
        self.set_timestamp()
        self.set_error_report_name(error_report_file_name)
        self.error_count: int = 0

    def set_error_report_name(self, error_report_file_name=None):
        if error_report_file_name:
            self.error_report_file_name = error_report_file_name
        else:
            self.error_report_file_name: str = (
                f"error-report-{self.get_timestamp()}.csv"
            )
        self.error_report_path = (
            Path(settings.TEMP) / self.error_folder / self.error_report_file_name
        )

    def download_s3_file(self):
        self.downloaded_file = download_file(self.s3_object_key, self.bucket_name)

    def set_sf_client(self, sf_client: SfClient):
        self.sf_client = sf_client

    def log_batch(
        self, results: list, data: list, salesforce_object: str, upsert_key: str
    ):
        """
        The intention here is to call this method after making a bulk upsert

        Parameters:
            results: The results from the Salesforce API
            data: The data you pushed
            salesforce_object: The name of the object you upserted to
            upsert_key: The upsert key you used
        """
        batch = (results, list(data), salesforce_object, upsert_key)
        _, errors = self.parse_sfdc_results(*batch)
        error_count = self.create_error_report_file(errors)
        self.error_count += error_count

    def automagically_finish_up(self):
        self.report()

    def parse_sfdc_results(self, *args):
        return parse_bulk_upsert_results(*args)

    def create_error_report_file(self, errors):
        return create_error_report(errors, self.error_report_path)

    def report(self):
        self.archive_file()
        self.upload_error_report()
        self.create_execution_object()

    def archive_file(self):
        move_file(self.s3_object_key, self.archive_file_s3_key, self.bucket_name)

    def upload_error_report(self):
        assert self.error_report_path, f"error_report_path is not set"
        return upload_file(
            self.error_report_path, self.bucket_name, self.error_file_s3_key
        )

    def set_timestamp(self, timestamp: str = None):
        self.timestamp = timestamp if timestamp else get_iso()

    def get_timestamp(self):
        return self.timestamp

    @property
    def archive_file_s3_key(self):
        s3_object_key = self.s3_object_key
        archive_folder = self.archive_folder if self.archive_folder else "archive"
        archive_s3_key = timestamp_s3_key(s3_object_key, timestamp=self.get_timestamp())
        return (Path(archive_folder) / archive_s3_key).as_posix()

    @property
    def error_file_s3_key(self):
        return (Path(self.error_folder) / self.error_report_file_name).as_posix()

    def create_execution_object(self):
        assert self.sf_client, f"sf_client isn't set"
        assert self.execution_object_name, f"execution_object_name isn't set"
        return getattr(self.sf_client, self.execution_object_name).create(
            self.execution_sfdc_hash
        )

    @property
    def execution_sfdc_hash(self):
        """
        The data to record in salesforce for this s3 event

        This function should return something like this

        return {
            "Origin_Path__c": self.self.s3_object_key,
            "Archive_Path__c": self.archive_file_s3_key,
            "Errors_Path__c": self.error_file_s3_key,
            "Errors_Count__c": self.error_count,
        }
        """
        raise NotImplementedError
