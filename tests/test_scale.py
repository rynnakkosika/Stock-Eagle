import pytest

from stock_eagle import scale


@pytest.mark.parametrize("text,expected", [
    ("Osta", 5), ("LISÄÄ", 4), ("pidä", 3), ("Vähennä", 2), ("myy", 1),
    ("Buy", 5), ("accumulate", 4), ("Hold", 3), ("reduce", 2), ("Sell", 1),
    ("strong_buy", 5), ("Strong Sell", 1), ("  neutral ", 3), ("köp", 5), ("sälj", 1),
])
def test_normalize_text(text, expected):
    assert scale.normalize_text(text) == expected


def test_normalize_text_unknown():
    assert scale.normalize_text("moon") is None
    assert scale.normalize_text(None) is None


def test_three_level():
    assert scale.normalize_three_level("buy") == 5
    assert scale.normalize_three_level("hold") == 3
    assert scale.normalize_three_level("sell") == 1
    assert scale.normalize_three_level("x") is None


def test_normalize_numeric():
    assert scale.normalize_numeric(1, 1, 5) == 1
    assert scale.normalize_numeric(5, 1, 5) == 5
    assert scale.normalize_numeric(0, 0, 10) == 1
    assert scale.normalize_numeric(10, 0, 10) == 5
    # lower-is-better scales (e.g. 1 = strong buy)
    assert scale.normalize_numeric(1, 1, 5, higher_is_better=False) == 5
    with pytest.raises(ValueError):
        scale.normalize_numeric(6, 1, 5)
    with pytest.raises(ValueError):
        scale.normalize_numeric(1, 1, 1)


def test_weighted_counts():
    mean, n = scale.weighted_counts({"strongBuy": 2, "buy": 2, "hold": 0, "sell": 0,
                                     "strongSell": 0})
    assert n == 4 and mean == pytest.approx(4.5)
    mean, n = scale.weighted_counts({"strongBuy": 1, "strongSell": 1})
    assert n == 2 and mean == pytest.approx(3.0)
    assert scale.weighted_counts({}) == (None, 0)
    assert scale.weighted_counts({"buy": None}) == (None, 0)
    with pytest.raises(ValueError):
        scale.weighted_counts({"buy": -1})


@pytest.mark.parametrize("rating,b,lab", [
    (1.0, 1, "Myy"), (1.49, 1, "Myy"), (1.5, 2, "Vähennä"), (2.5, 3, "Pidä"),
    (3.49, 3, "Pidä"), (3.5, 4, "Lisää"), (4.5, 5, "Osta"), (5.0, 5, "Osta"),
    (7.0, 5, "Osta"), (0.0, 1, "Myy"),
])
def test_bucket_and_label(rating, b, lab):
    assert scale.bucket(rating) == b
    assert scale.label(rating) == lab


def test_label_none():
    assert scale.bucket(None) is None
    assert scale.label(None) == "–"
    assert scale.bucket(float("nan")) is None
