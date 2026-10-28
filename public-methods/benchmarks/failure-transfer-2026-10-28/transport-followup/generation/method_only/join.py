def _blank(key):
    return key is None or key.strip() == ""


def solve(payload):
    left, right = payload["left"], payload["right"]
    expected = payload.get("expected_cardinality")
    lc, rc = {}, {}
    lb = rb = 0
    for row in left:
        k = row["key"]
        if _blank(k): lb += 1
        else: lc[k] = lc.get(k, 0) + 1
    for row in right:
        k = row["key"]
        if _blank(k): rb += 1
        else: rc[k] = rc.get(k, 0) + 1
    shared = lc.keys() & rc.keys()
    ml, mr = sum(lc[k] for k in shared), sum(rc[k] for k in shared)
    inner = sum(lc[k] * rc[k] for k in shared)
    ul, ur = len(left) - ml, len(right) - mr
    if not shared:
        actual = "none"
    else:
        lrep = any(lc[k] > 1 for k in shared)
        rrep = any(rc[k] > 1 for k in shared)
        actual = {(False,False):"one_to_one", (True,False):"many_to_one",
                  (False,True):"one_to_many", (True,True):"many_to_many"}[(lrep,rrep)]
    if expected is None: satisfied = None
    elif expected == "one_to_one":
        satisfied = all(n == 1 for n in lc.values()) and all(n == 1 for n in rc.values())
    elif expected == "one_to_many": satisfied = all(n == 1 for n in lc.values())
    elif expected == "many_to_one": satisfied = all(n == 1 for n in rc.values())
    elif expected == "many_to_many": satisfied = True
    else: satisfied = False
    return {
        "left_blank": lb, "right_blank": rb,
        "left_duplicate_rows": sum(n for n in lc.values() if n > 1),
        "right_duplicate_rows": sum(n for n in rc.values() if n > 1),
        "matched_left_rows": ml, "matched_right_rows": mr,
        "unmatched_left_rows": ul, "unmatched_right_rows": ur,
        "inner_rows": inner, "left_join_rows": inner + ul,
        "full_join_rows": inner + ul + ur, "actual_cardinality": actual,
        "expected_satisfied": satisfied,
    }