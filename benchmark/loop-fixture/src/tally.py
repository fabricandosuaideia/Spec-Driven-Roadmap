def tally(votes):
    """Count votes per item id. Returns {item_id: count}."""
    out = {}
    for v in votes:
        out[v] = out.get(v, 0) + 1
    return out


def rank(votes):
    """Items ordered by vote count, most first."""
    counts = tally(votes)
    return sorted(counts, key=lambda k: -counts[k])
