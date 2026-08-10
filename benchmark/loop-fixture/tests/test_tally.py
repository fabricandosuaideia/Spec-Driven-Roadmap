from src.tally import tally, rank


def test_counts_votes():
    assert tally(["a", "b", "a"]) == {"a": 2, "b": 1}


def test_rank_orders_by_count():
    assert rank(["a", "b", "a"]) == ["a", "b"]


def test_tie_breaks_by_earliest_proposal():
    # Spec says: on equal votes, the item proposed FIRST wins.
    # "b" was proposed before "a" in this fixture's ordering.
    assert rank(["a", "b"]) == ["b", "a"]
