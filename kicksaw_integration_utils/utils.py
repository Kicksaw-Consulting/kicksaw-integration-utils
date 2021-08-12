import datetime
import itertools

from typing import Iterable
from pathlib import Path


def get_iso() -> str:
    """
    Get an iso timestamp with less precision than .iso() returns, and no special characters
    """
    return datetime.datetime.now().strftime("%Y%m%dT%H%M")


def get_timestamp_folder(datetime_object: datetime.datetime = None) -> Path:
    """
    Returns a Path object that's a timestamped folder path

    e.g., ts_folder = 2021/03/27
        so you can do Path("some/path") / ts_folder / <your_file>.txt

    Defaults to datetime.datetime.now() if nothing's passed in
    """
    if not datetime_object:
        datetime_object = datetime.datetime.now()

    year = datetime_object.strftime("%Y")
    month = datetime_object.strftime("%m")
    day = datetime_object.strftime("%d")

    return Path(year) / month / day


def batch_collection(iterable: Iterable, size: int):
    """
    takes in an iterable, and divides the elements into batches,
    return a generator for performance reasons

    Stolen from https://stackoverflow.com/a/8991553/8395007
    """
    it = iter(iterable)
    while True:
        chunk = list(itertools.islice(it, size))
        if not chunk:
            break
        yield chunk


def dedupe(elements: list, unique_prop: str) -> list:
    seen_unique_props = set()
    deduped_elements = list()

    for element in elements:
        if isinstance(element, dict):
            unique_value = element[unique_prop]
        else:
            unique_value = getattr(element, unique_prop)

        if unique_value in seen_unique_props:
            continue

        seen_unique_props.add(unique_value)
        deduped_elements.append(element)

    return deduped_elements