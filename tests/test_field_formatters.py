import pytest

from kicksaw_integration_utils.field_formatters import convert_to_iso_date


@pytest.mark.parametrize(
    "date_string,expected_date",
    [
        ("19700122", "1970-01-22"),
        ("19851118", "1985-11-18"),
        ("19990516", "1999-05-16"),
        ("1999/05/16", "1999-05-16"),
        ("/05/16", None),
        ("99999999", None),
        ("19870229", None),
        ("19522201", None),
        ("1999a215", None),
        (None, None),
    ],
)
def test_format_date(date_string, expected_date):
    result = convert_to_iso_date(date_string)
    assert result == expected_date
