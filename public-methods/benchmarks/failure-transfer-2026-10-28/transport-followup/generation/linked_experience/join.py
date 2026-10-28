from collections import Counter


def _blank(key):
    return key is None or key.strip() == ""


def solve(payload):
    left = payload["left"]
    right = payload["right"]
    left_counts = Counter(row["key"] for row in left if not _blank(row["key"]))
    right_counts = Counter(row["key"] for row in right if not _blank(row["key"]))
    shared = left_counts.keys() & right_counts.keys()

    left_blank = sum(1 for row in left if _blank(row["key"]))
    right_blank = sum(1 for row in right if _blank(row["key"]))
    left_duplicate_rows = sum(count for count in left_counts.values() if count > 1)
    right_duplicate_rows = sum(count for count in right_counts.values() if count > 1)
    matched_left_rows = sum(left_counts[key] for key in shared)
    matched_right_rows = sum(right_counts[key] for key in shared)
    unmatched_left_rows = len(left) - matched_left_rows
    unmatched_right_rows = len(right) - matched_right_rows
    inner_rows = sum(left_counts[key] * right_counts[key] for key in shared)

    if not shared:
        actual_cardinality = "none"
    else:
        left_repeats = any(left_counts[key] > 1 for key in shared)
        right_repeats = any(right_counts[key] > 1 for key in shared)
        if left_repeats and right_repeats:
            actual_cardinality = "many_to_many"
        elif left_repeats:
            actual_cardinality = "many_to_one"
        elif right_repeats:
            actual_cardinality = "one_to_many"
        else:
            actual_cardinality = "one_to_one"

    expected = payload.get("expected_cardinality")
    if expected is None:
        expected_satisfied = None
    elif expected == "one_to_one":
        expected_satisfied = not left_duplicate_rows and not right_duplicate_rows
    elif expected == "one_to_many":
        expected_satisfied = not left_duplicate_rows
    elif expected == "many_to_one":
        expected_satisfied = not right_duplicate_rows
    elif expected == "many_to_many":
        expected_satisfied = True
    else:
        expected_satisfied = False

    return {
        "left_blank": left_blank,
        "right_blank": right_blank,
        "left_duplicate_rows": left_duplicate_rows,
        "right_duplicate_rows": right_duplicate_rows,
        "matched_left_rows": matched_left_rows,
        "matched_right_rows": matched_right_rows,
        "unmatched_left_rows": unmatched_left_rows,
        "unmatched_right_rows": unmatched_right_rows,
        "inner_rows": inner_rows,
        "left_join_rows": inner_rows + unmatched_left_rows,
        "full_join_rows": inner_rows + unmatched_left_rows + unmatched_right_rows,
        "actual_cardinality": actual_cardinality,
        "expected_satisfied": expected_satisfied,
    }