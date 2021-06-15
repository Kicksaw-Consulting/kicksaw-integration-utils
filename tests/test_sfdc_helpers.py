from kicksaw_integration_utils.sfdc_helpers import extract_errors_from_results


def test_extract_errors_from_results():
    results = [
        {"success": True},
        {"success": False, "errors": [1]},
        {"success": False, "errors": [2]},
    ]

    errors = extract_errors_from_results(results)

    assert len(errors) == 2
    assert errors == [1, 2]
