import datetime


def convert_to_iso_date(date):
    """
    Adds delimiter to a date
        e.g. '20220101' => '2022-01-01'
    """
    if not date:
        return None

    # Removes all non numbers from date string
    numeric_filter = filter(str.isdigit, date)
    numeric_string = "".join(numeric_filter)

    # Handle empty dates
    if numeric_string.strip() == "":
        return None
    elif len(numeric_string) == 8:
        year, month, day = [numeric_string[:4], numeric_string[4:6], numeric_string[6:]]
        try:
            # Handle invalid dates
            date_object = datetime.datetime(int(year), int(month), int(day))
            return date_object.strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None
