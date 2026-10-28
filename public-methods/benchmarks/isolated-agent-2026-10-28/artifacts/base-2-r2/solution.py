import json
import sys


def rounded(value):
    # Normalize negative zero and keep the result a JSON number.
    value = round(value, 6)
    return 0 if value == 0 else value


def analyze(records, min_n, min_gain_pp, include_missing):
    groups = {
        "A": {"n": 0, "success": 0},
        "B": {"n": 0, "success": 0},
    }
    for record in records:
        outcome = record["outcome"]
        if outcome == "missing" and not include_missing:
            continue
        group = groups[record["variant"]]
        group["n"] += 1
        if outcome == "success":
            group["success"] += 1

    for group in groups.values():
        group["rate"] = group["success"] / group["n"] if group["n"] else None

    a_rate = groups["A"]["rate"]
    b_rate = groups["B"]["rate"]
    uplift = (b_rate - a_rate) * 100 if a_rate is not None and b_rate is not None else None
    enough = groups["A"]["n"] >= min_n and groups["B"]["n"] >= min_n
    passed = enough and uplift is not None and uplift >= min_gain_pp

    result_groups = {}
    for variant in ("A", "B"):
        group = groups[variant]
        result_groups[variant] = {
            "n": group["n"],
            "success": group["success"],
            "rate": rounded(group["rate"]) if group["rate"] is not None else None,
        }
    return {
        "A": result_groups["A"],
        "B": result_groups["B"],
        "uplift_pp": rounded(uplift) if uplift is not None else None,
        "decision": "pass" if passed else "hold",
    }


def main():
    data = json.load(sys.stdin)
    latest = {}
    for record in data["records"]:
        participant = record["participant_id"]
        key = (record["revision"], record["record_id"])
        if participant not in latest or key > latest[participant][0]:
            latest[participant] = (key, record)

    removed_duplicates = len(data["records"]) - len(latest)
    final_records = [entry[1] for entry in latest.values()]
    eligible_records = [record for record in final_records if record["eligible"]]
    excluded_ineligible = len(final_records) - len(eligible_records)

    result = {
        "removed_duplicates": removed_duplicates,
        "excluded_ineligible": excluded_ineligible,
        "analyses": {
            "exclude_missing": analyze(eligible_records, data["min_n"], data["min_gain_pp"], False),
            "missing_as_failure": analyze(eligible_records, data["min_n"], data["min_gain_pp"], True),
        },
    }
    json.dump(result, sys.stdout, separators=(",", ":"), allow_nan=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
