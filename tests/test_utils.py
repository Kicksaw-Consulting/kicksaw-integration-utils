import datetime

import pytest

from kicksaw_integration_utils.utils import (
    dedupe,
    get_timestamp_folder,
    batch_collection,
)


def test_get_timestamp_folder():
    dt = datetime.datetime(year=2021, month=3, day=27)
    folder = get_timestamp_folder(dt)
    assert "2021/03/27" == folder.as_posix()


def test_batch():
    collection = [1, 2, 3, 4, 5]

    batches = batch_collection(collection, 2)

    # returns generator, must loop and check explicitly
    for idx, batch_ in enumerate(batches):
        if idx == 0:
            assert batch_ == [1, 2]
        elif idx == 1:
            assert batch_ == [3, 4]
        else:
            assert batch_ == [5]


class Dud:
    def __init__(self, id) -> None:
        self.id = id

    def __eq__(self, o: object) -> bool:
        return self.id == o.id


@pytest.mark.parametrize(
    "data,key,deduped_data",
    [
        (
            [{"id": 1}, {"id": 1}, {"id": 2, "name": "test"}],
            "id",
            [{"id": 1}, {"id": 2, "name": "test"}],
        ),
        ([Dud(1), Dud(2), Dud(2), Dud(3)], "id", [Dud(1), Dud(2), Dud(3)]),
    ],
)
def test_dedupe(data, key, deduped_data):
    assert dedupe(data, key) == deduped_data