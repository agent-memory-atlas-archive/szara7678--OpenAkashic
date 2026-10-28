from collections import Counter


def _blank(value):
    return value is None or (isinstance(value, str) and value.strip() == "")


def _key_counts(rows):
    counts = Counter()
    blanks = 0
    for row in rows:
        key = row["key"]
        if _blank(key):
            blanks += 1
        else:
            counts[key] += 1
    return counts, blanks


def _duplicate_rows(counts):
    return sum(count for count in counts.values() if count > 1)


def solve(payload):
    left_counts, left_blank = _key_counts(payload["left"])
    right_counts, right_blank = _key_counts(payload["right"])
    shared = left_counts.keys() & right_counts.keys()

    inner_rows = sum(left_counts[key] * right_counts[key] for key in shared)
    matched_left = sum(left_counts[key] for key in shared)
    matched_right = sum(right_counts[key] for key in shared)
    left_total = len(payload["left"])
    right_total = len(payload["right"])
    unmatched_left = left_total - matched_left
    unmatched_right = right_total - matched_right

    if not shared:
        actual = "none"
    else:
        left_repeats = any(left_counts[key] > 1 for key in shared)
        right_repeats = any(right_counts[key] > 1 for key in shared)
        if left_repeats and right_repeats:
            actual = "many_to_many"
        elif left_repeats:
            actual = "many_to_one"
        elif right_repeats:
            actual = "one_to_many"
        else:
            actual = "one_to_one"

    expected = payload.get("expected_cardinality")
    if expected is None:
        satisfied = None
    elif expected == "one_to_one":
        satisfied = all(count == 1 for count in left_counts.values()) and all(
            count == 1 for count in right_counts.values()
        )
    elif expected == "one_to_many":
        satisfied = all(count == 1 for count in left_counts.values())
    elif expected == "many_to_one":
        satisfied = all(count == 1 for count in right_counts.values())
    else:
        satisfied = True

    inner_rows = int(inner_rows)
    return {
        "left_blank": left_blank,
        "right_blank": right_blank,
        "left_duplicate_rows": _duplicate_rows(left_counts),
        "right_duplicate_rows": _duplicate_rows(right_counts),
        "matched_left_rows": matched_left,
        "matched_right_rows": matched_right,
        "unmatched_left_rows": unmatched_left,
        "unmatched_right_rows": unmatched_right,
        "inner_rows": inner_rows,
        "left_join_rows": inner_rows + unmatched_left,
        "full_join_rows": inner_rows + unmatched_left + unmatched_right,
        "actual_cardinality": actual,
        "expected_satisfied": satisfied,
    }
