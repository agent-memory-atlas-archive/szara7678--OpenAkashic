from collections import Counter

def _blank(v):
    return v is None or v.strip() == ""

def solve(payload):
    left, right = payload["left"], payload["right"]
    lc, rc = Counter(), Counter()
    lb = rb = 0
    for row in left:
        k = row["key"]
        if _blank(k): lb += 1
        else: lc[k] += 1
    for row in right:
        k = row["key"]
        if _blank(k): rb += 1
        else: rc[k] += 1
    ld = sum(n for n in lc.values() if n > 1)
    rd = sum(n for n in rc.values() if n > 1)
    shared = lc.keys() & rc.keys()
    inner = sum(lc[k] * rc[k] for k in shared)
    ml, mr = sum(lc[k] for k in shared), sum(rc[k] for k in shared)
    ul, ur = len(left) - ml, len(right) - mr
    if not shared: actual = "none"
    else:
        lr, rr = any(lc[k] > 1 for k in shared), any(rc[k] > 1 for k in shared)
        actual = "many_to_many" if lr and rr else "many_to_one" if lr else "one_to_many" if rr else "one_to_one"
    exp = payload.get("expected_cardinality")
    if exp is None: ok = None
    elif exp == "one_to_one": ok = all(n == 1 for n in lc.values()) and all(n == 1 for n in rc.values())
    elif exp == "one_to_many": ok = all(n == 1 for n in lc.values())
    elif exp == "many_to_one": ok = all(n == 1 for n in rc.values())
    elif exp == "many_to_many": ok = True
    else: ok = False
    return dict(left_blank=lb, right_blank=rb, left_duplicate_rows=ld, right_duplicate_rows=rd, matched_left_rows=ml, matched_right_rows=mr, unmatched_left_rows=ul, unmatched_right_rows=ur, inner_rows=inner, left_join_rows=inner+ul, full_join_rows=inner+ul+ur, actual_cardinality=actual, expected_satisfied=ok)
