from collections import Counter

def _blank(key):
    return key is None or key.strip() == ""

def solve(payload):
    left, right = payload["left"], payload["right"]
    expected = payload.get("expected_cardinality")
    lc = Counter(r["key"] for r in left if not _blank(r["key"]))
    rc = Counter(r["key"] for r in right if not _blank(r["key"]))
    shared = lc.keys() & rc.keys()
    ml, mr = sum(lc[k] for k in shared), sum(rc[k] for k in shared)
    inner = sum(lc[k] * rc[k] for k in shared)
    ul, ur = len(left)-ml, len(right)-mr
    lr = any(lc[k] > 1 for k in shared)
    rr = any(rc[k] > 1 for k in shared)
    if not shared: actual = "none"
    elif lr and rr: actual = "many_to_many"
    elif lr: actual = "many_to_one"
    elif rr: actual = "one_to_many"
    else: actual = "one_to_one"
    if expected is None: satisfied = None
    elif expected == "one_to_one": satisfied = all(v == 1 for v in lc.values()) and all(v == 1 for v in rc.values())
    elif expected == "one_to_many": satisfied = all(v == 1 for v in lc.values())
    elif expected == "many_to_one": satisfied = all(v == 1 for v in rc.values())
    elif expected == "many_to_many": satisfied = True
    else: satisfied = False
    return {
        "left_blank":sum(_blank(r["key"]) for r in left),"right_blank":sum(_blank(r["key"]) for r in right),
        "left_duplicate_rows":sum(v for v in lc.values() if v > 1),"right_duplicate_rows":sum(v for v in rc.values() if v > 1),
        "matched_left_rows":ml,"matched_right_rows":mr,"unmatched_left_rows":ul,"unmatched_right_rows":ur,
        "inner_rows":inner,"left_join_rows":inner+ul,"full_join_rows":inner+ul+ur,
        "actual_cardinality":actual,"expected_satisfied":satisfied
    }
