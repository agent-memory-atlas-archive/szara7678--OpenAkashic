def _blank(value):
    return value is None or value.strip() == ""


def solve(payload):
    left = payload["left"]
    right = payload["right"]
    expected = payload.get("expected_cardinality")
    left_counts = {}
    right_counts = {}
    left_blank = right_blank = 0

    for row in left:
        key = row["key"]
        if _blank(key):
            left_blank += 1
        else:
            left_counts[key] = left_counts.get(key, 0) + 1
    for row in right:
        key = row["key"]
        if _blank(key):
            right_blank += 1
        else:
            right_counts[key] = right_counts.get(key, 0) + 1

    left_dups = sum(count for count in left_counts.values() if count > 1)
    right_dups = sum(count for count in right_counts.values() if count > 1)
    shared = left_counts.keys() & right_counts.keys()
    inner = sum(left_counts[key] * right_counts[key] for key in shared)
    matched_left = sum(left_counts[key] for key in shared)
    matched_right = sum(right_counts[key] for key in shared)
    unmatched_left = len(left) - left_blank - matched_left
    unmatched_right = len(right) - right_blank - matched_right

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

    if expected is None:
        expected_satisfied = None
    elif expected == "one_to_one":
        expected_satisfied = left_dups == 0 and right_dups == 0
    elif expected == "one_to_many":
        expected_satisfied = left_dups == 0
    elif expected == "many_to_one":
        expected_satisfied = right_dups == 0
    elif expected == "many_to_many":
        expected_satisfied = True
    else:
        expected_satisfied = False

    return {
        "left_blank": left_blank,
        "right_blank": right_blank,
        "left_duplicate_rows": left_dups,
        "right_duplicate_rows": right_dups,
        "matched_left_rows": matched_left,
        "matched_right_rows": matched_right,
        "unmatched_left_rows": unmatched_left,
        "unmatched_right_rows": unmatched_right,
        "inner_rows": inner,
        "left_join_rows": inner + unmatched_left,
        "full_join_rows": inner + unmatched_left + unmatched_right,
        "actual_cardinality": actual,
        "expected_satisfied": expected_satisfied,
    }