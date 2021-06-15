from typing import Tuple


def parse_bulk_upsert_results(
    results: list, data: list, salesforce_object: str, upsert_key: str
) -> Tuple[list, list]:
    """
    Parses the results of a bulk upsert call, collecting errors and successes

    # TODO: allow a custom serializer for errors
    # TODO: do something more with successes
    """
    assert len(results) == len(
        data
    ), f"Results ({len(results)}) and upload data ({len(data)}) have different lengths!"

    successes = list()
    errors = list()
    for result, pushed in zip(results, data):
        if result.get("success"):
            successes.append(result)
        for error in result.get("errors"):
            errors.append(
                {
                    "salesforce_object": salesforce_object,
                    "code": error.get("statusCode"),
                    "message": error.get("message"),
                    "upsert_key": upsert_key,
                    "upsert_key_value": pushed[upsert_key],
                    "object_json": pushed,
                }
            )
    return successes, errors


def extract_errors_from_results(results: list) -> list:
    """
    More general version of parse_bulk_upsert_results
    """
    errors = list()
    for result in results:
        success = result.get("success")
        if not success:
            errors += result.get("errors")
    return errors