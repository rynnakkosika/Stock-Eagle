from datetime import date

import pytest

from stock_eagle import changes as CH

from .conftest import rec


def test_upgrade_and_downgrade_detected():
    history = [
        rec(rating=3, date="2026-07-01", target=10),
        rec(rating=4, date="2026-08-01", target=11),
        rec(rating=2, date="2026-09-01", target=8),
    ]
    out = CH.detect_changes(history)
    assert [c.kind for c in out] == [CH.DOWNGRADE, CH.UPGRADE]  # newest first
    down, up = out
    assert up.old_label == "Pidä" and up.new_label == "Lisää" and up.direction == 1
    assert down.old_label == "Lisää" and down.new_label == "Vähennä" and down.direction == -1
    assert down.target_change_pct == pytest.approx(8 / 11 - 1)


def test_identical_snapshots_produce_no_change():
    assert CH.detect_changes([rec(rating=3, target=10), rec(rating=3, target=10,
                                                            fetched="2026-10-09")]) == []


def test_small_rating_move_within_bucket_is_not_a_change():
    # aggregate means 3.2 → 3.4 both round to "Pidä"
    assert CH.detect_changes([rec(rating=3.2, date="2026-08-01"),
                              rec(rating=3.4, date="2026-09-01")]) == []


def test_bucket_cross_for_aggregate():
    out = CH.detect_changes([rec(rating=3.4, date="2026-08-01"),
                             rec(rating=3.6, date="2026-09-01")])
    assert len(out) == 1 and out[0].kind == CH.UPGRADE


def test_target_only_change():
    out = CH.detect_changes([rec(rating=4, target=10, date="2026-08-01"),
                             rec(rating=4, target=12, date="2026-09-01")])
    assert len(out) == 1
    c = out[0]
    assert c.kind == CH.TARGET_ONLY and c.direction == 0
    assert c.target_change_pct == pytest.approx(0.2)


def test_target_appears_counts_as_change():
    out = CH.detect_changes([rec(rating=4, target=None, date="2026-08-01"),
                             rec(rating=4, target=12, date="2026-09-01")])
    assert out[0].kind == CH.TARGET_ONLY and out[0].target_change_pct is None


def test_groups_are_independent():
    out = CH.detect_changes([
        rec("AAA", "s1", 3, date="2026-08-01"),
        rec("AAA", "s2", 5, date="2026-09-01"),  # different source, first snapshot
        rec("BBB", "s1", 1, date="2026-09-01"),
    ])
    assert out == []


def test_include_initial():
    out = CH.detect_changes([rec(rating=5)], include_initial=True)
    assert out[0].kind == CH.INITIATED


def test_recent_window():
    cs = CH.detect_changes([rec(rating=3, date="2026-01-01"), rec(rating=4, date="2026-10-20"),
                            rec(rating=3, date="2026-11-05")])
    assert len(cs) == 2
    assert len(CH.recent(cs, 7, today=date(2026, 11, 9))) == 1
    assert len(CH.recent(cs, 30, today=date(2026, 11, 9))) == 2
