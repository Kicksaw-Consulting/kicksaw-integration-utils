import datetime

from kicksaw_integration_utils.utils import get_timestamp_folder, batch_collection


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
