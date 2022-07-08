import datetime

import pytest

from kicksaw_integration_utils.utils import (
    dedupe,
    get_timestamp_folder,
    batch_collection,
    extract_domain,
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


@pytest.mark.parametrize(
    "url,domain,remove_subdomains",
    [
        ("https://www.google.com/", "google.com", False),
        (
            "https://www.amazon.com/s?k=gaming+keyboard&pd_rd_r=7d0a067b-c9ff-4815-ac9a-692a459d37c2&pd_rd_w=oxSxd&pd_rd_wg=3eEqP&pf_rd_p=12129333-2117-4490-9c17-6d31baf0582a&pf_rd_r=H9BERTBPN8CZYP2GEADE&ref=pd_gw_unk",
            "amazon.com",
            False,
        ),
        ("https://github.com/python-poetry/poetry/issues/1763", "github.com", False),
        (
            "https://blog.sifdata.com/10-best-ways-increase-sales-effectiveness-complete-guide/",
            "sifdata.com",
            True,
        ),
        ("https://codepen.io", "codepen.io", False),
        ("https://io", None, False),
        ("http://a.io/what", "a.io", True),
    ],
)
def test_extract_domain(url, domain, remove_subdomains):
    assert extract_domain(url, remove_subdomains=remove_subdomains) == domain