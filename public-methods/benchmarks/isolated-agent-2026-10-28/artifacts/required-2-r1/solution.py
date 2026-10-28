import json
import sys


def summarize(records, missing_as_failure, min_n, min_gain_pp):
    groups = {
        "A": {"n": 0, "success": 0},
        "B": {"n": 0, "success": 0},
    }
    for record in records:
        outcome = record["outcome"]
        if outcome == "missing" and not missing_as_failure:
            continue
        group = groups[record["variant"]]
        group["n"] += 1
        if outcome == "success":
            group["success"] += 1

    for group in groups.values():
        group["rate"] = (
            round(group["success"] / group["n"], 6) if group["n"] else None
        )

    if groups["A"]["n"] and groups["B"]["n"]:
        uplift = (
            groups["B"]["success"] / groups["B"]["n"]
            - groups["A"]["success"] / groups["A"]["n"]
        ) * 100
        uplift_output = round(uplift, 6)
    else:
        uplift = None
        uplift_output = None

    passed = (
        groups["A"]["n"] >= min_n
        and groups["B"]["n"] >= min_n
        and uplift is not None
        and uplift >= min_gain_pp
    )
    return {
        "A": groups["A"],
        "B": groups["B"],
        "uplift_pp": uplift_output,
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

    final_records = [entry[1] for entry in latest.values()]
    removed_duplicates = len(data["records"]) - len(final_records)
    eligible_records = [r for r in final_records if r["eligible"]]
    excluded_ineligible = len(final_records) - len(eligible_records)

    result = {
        "removed_duplicates": removed_duplicates,
        "excluded_ineligible": excluded_ineligible,
        "analyses": {
            "exclude_missing": summarize(
                eligible_records, False, data["min_n"], data["min_gain_pp"]
            ),
            "missing_as_failure": summarize(
                eligible_records, True, data["min_n"], data["min_gain_pp"]
            ),
        },
    }
    json.dump(result, sys.stdout, separators=(",", ":"), allow_nan=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
