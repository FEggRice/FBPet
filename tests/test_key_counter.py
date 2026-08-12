import pytest

from pet.key_counter import KeyCounter


def test_register_increments_per_key_and_total():
    c = KeyCounter(threshold=100)
    c.register(65)  # A
    c.register(65)  # A
    c.register(66)  # B

    assert c.get_count(65) == 2
    assert c.get_count(66) == 1
    assert c.total == 3


def test_reminder_fires_every_threshold():
    c = KeyCounter(threshold=100)
    hits = []
    c.on_reminder(hits.append)

    for _ in range(200):
        c.register(65)

    assert hits == [100, 200]
    assert c.total == 200


def test_no_reminder_before_threshold():
    c = KeyCounter(threshold=100)
    hits = []
    c.on_reminder(hits.append)

    for _ in range(99):
        c.register(65)

    assert hits == []
    assert c.total == 99


def test_to_dict_from_dict_round_trip():
    c = KeyCounter(threshold=100)
    c.register(65)
    c.register(65)
    c.register(66)

    loaded = KeyCounter.from_dict(c.to_dict(), threshold=100)

    assert loaded.get_count(65) == 2
    assert loaded.get_count(66) == 1
    assert loaded.total == 3


def test_from_dict_empty_or_invalid_returns_fresh():
    assert KeyCounter.from_dict(None, threshold=100).total == 0
    assert KeyCounter.from_dict({"Total": 7, "Counts": {"bogus": "x"}}, threshold=100).total == 7
    assert KeyCounter.from_dict({"Total": 7, "Counts": {"65": 3}}, threshold=100).get_count(65) == 3
