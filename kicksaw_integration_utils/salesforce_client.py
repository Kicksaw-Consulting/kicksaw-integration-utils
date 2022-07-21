import requests
import time

from simple_salesforce import Salesforce
from simple_salesforce.bulk import (
    SFBulkHandler as BaseSFBulkHandler,
    SFBulkType as BaseSFBulkType,
)
from simple_salesforce.exceptions import SalesforceMalformedRequest


class SFBulkType(BaseSFBulkType):
    def __init__(self, object_name, bulk_url, headers, session):
        super().__init__(object_name, bulk_url, headers, session)

        self.attempts = 0
        self.max_attempts = 5

    def _bulk_operation(
        self,
        *args,
        batch_size=10000,
        **kwargs,
    ):
        try:
            return super()._bulk_operation(
                *args,
                batch_size=batch_size,
                **kwargs,
            )
        except SalesforceMalformedRequest as exception:
            if "Exceeded max size limit" in str(exception):
                new_batch_size = batch_size - 1000
                assert new_batch_size > 0, "Batch Size Too Low!"
                print(
                    f"Payload too large. Retrying with a lower batch size. {batch_size} -> {new_batch_size}"
                )
                return super()._bulk_operation(
                    *args,
                    batch_size=new_batch_size,
                    **kwargs,
                )
            raise exception

    def _get_batch_results(self, job_id, batch_id, operation):
        try:
            batch_result = super()._get_batch_results(job_id, batch_id, operation)
        except requests.ConnectionError as reason:
            if self.attempts < self.max_attempts:
                self.attempts += 1
                time.sleep(2 ** self.attempts)
                return self._get_batch_results(job_id, batch_id, operation)
            raise reason
        return batch_result


class SFBulkHandler(BaseSFBulkHandler):
    def __getattr__(self, name):
        """
        Source code from simple salesforce, but with SFBulkType swapped out
        for a subclassed version with back-off handling due to excessive
        payload size
        """
        return SFBulkType(
            object_name=name,
            bulk_url=self.bulk_url,
            headers=self.headers,
            session=self.session,
        )


class SfClient(Salesforce):
    def __init__(self, username, password, security_token, domain):
        config = {
            "username": username,
            "password": password,
            "security_token": security_token,
        }
        if domain and domain.lower() != "na":
            config["domain"] = domain

        super().__init__(**config)

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
