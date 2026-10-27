"""Bounded, read-only connectors for deliberately selected public subjects.

Upstream prose is evidence, never executable instructions. No LLM or private
vault is involved. Only these fixed HTTPS origins may be requested.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ALLOWED_HOSTS = {"www.wikidata.org", "api.github.com", "opendart.fss.or.kr", "openapi.naver.com"}
USER_AGENT = "OpenAkashicResearch/0.1 (+https://openakashic.com)"
QID = re.compile(r"Q[1-9][0-9]{0,11}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}\Z")


class SourceError(Exception):
    def __init__(self, reason, status=None):
        super().__init__(reason)
        self.reason, self.status = reason, status


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_json(url, headers=None):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password:
        raise SourceError("origin_not_allowed")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})})
    try:
        with build_opener(NoRedirect()).open(request, timeout=12) as response:
            raw = response.read(4_000_001)
        if len(raw) > 4_000_000:
            raise SourceError("response_too_large")
        return json.loads(raw.decode("utf-8-sig"))
    except HTTPError as exc:
        # Never include URL/response bodies: API query strings may contain keys.
        raise SourceError("upstream_http_" + str(exc.code), exc.code) from None
    except (URLError, TimeoutError, OSError):
        raise SourceError("upstream_unavailable") from None
    except (UnicodeError, ValueError):
        raise SourceError("invalid_upstream_json") from None


def failed(source_id, scope_key, reason, status="unavailable"):
    return {"source_id": source_id, "scope_key": scope_key, "status": status,
            "reason": reason, "coverage": {"content_collected": False}, "evidence": [], "facts": []}


def evidence(external_id, source_uri, content, excerpt, source_time=None, coverage=None):
    return {"external_id": external_id, "source_uri": source_uri, "content": content,
            "excerpt": excerpt, "source_time": source_time, "coverage": coverage or {"selected_fields_only": True}}


def fact(predicate, value, ref):
    return {"predicate": predicate, "value": value, "evidence_external_id": ref,
            "epistemic_state": "source_observation"}


def collect_wikidata(qid):
    scope = "entity:" + str(qid) + ":selected-v1"
    if not QID.fullmatch(qid or ""):
        return failed("wikidata", scope, "valid_qid_required", "not_found")
    try:
        raw = read_json("https://www.wikidata.org/wiki/Special:EntityData/" + qid + ".json")
        item = raw.get("entities", {}).get(qid)
        if not item or "missing" in item:
            return failed("wikidata", scope, "entity_not_found", "not_found")
        labels = {lang: row["value"] for lang, row in item.get("labels", {}).items() if lang in {"ko", "en"}}
        descriptions = {lang: row["value"] for lang, row in item.get("descriptions", {}).items() if lang in {"ko", "en"}}
        aliases = {lang: [row["value"] for row in rows[:10]] for lang, rows in item.get("aliases", {}).items() if lang in {"ko", "en"}}
        claims = {}
        totals = {}
        for prop in ("P31", "P856", "P1324", "P178", "P112", "P159", "P571", "P17"):
            rows = [row for row in item.get("claims", {}).get(prop, []) if row.get("rank") != "deprecated" and "datavalue" in row.get("mainsnak", {})]
            totals[prop] = len(rows)
            claims[prop] = [{"statement_id": row.get("id"), "value": row["mainsnak"]["datavalue"]["value"],
                             "rank": row.get("rank"), "references": row.get("references", [])} for row in rows[:5]]
        content = {"id": qid, "revision": item.get("lastrevid"), "labels": labels,
                   "descriptions": descriptions, "aliases": aliases, "claims": claims}
        ref = qid
        uri = "https://www.wikidata.org/w/index.php?" + urlencode({"title": qid, "oldid": item.get("lastrevid")})
        coverage = {"selected_fields_only": True, "languages": ["ko", "en"], "claim_counts": totals,
                    "max_claims_per_property": 5, "all_entity_facts_collected": False}
        excerpt = descriptions.get("ko") or descriptions.get("en") or labels.get("ko") or labels.get("en") or qid
        facts = [fact("name", labels, ref), fact("description", descriptions, ref)]
        for prop, rows in claims.items():
            if rows:
                facts.append(fact("wikidata." + prop, [r["value"] for r in rows], ref))
        return {"source_id": "wikidata", "scope_key": scope, "status": "ok", "coverage": coverage,
                "evidence": [evidence(ref, uri, content, excerpt, item.get("modified"), coverage)], "facts": facts}
    except SourceError as exc:
        return failed("wikidata", scope, exc.reason, "not_found" if exc.status == 404 else "unavailable")
    except (KeyError, TypeError):
        return failed("wikidata", scope, "invalid_upstream_schema")


def collect_github(repo):
    scope = "repo:" + str(repo).lower() + ":latest-release-v1"
    if not REPO.fullmatch(repo or "") or any(part in {".", ".."} for part in repo.split("/")):
        return failed("github", scope, "valid_repository_required", "not_found")
    base = "https://api.github.com/repos/" + repo
    try:
        raw = read_json(base)
        content = {key: raw.get(key) for key in ("id", "full_name", "description", "html_url", "homepage", "language", "archived")}
        content["owner_login"] = raw.get("owner", {}).get("login")
        content["license_spdx"] = (raw.get("license") or {}).get("spdx_id")
        try:
            release = read_json(base + "/releases/latest")
        except SourceError as exc:
            if exc.status != 404:
                raise
            release = None
        content["latest_release"] = ({key: release.get(key) for key in ("id", "tag_name", "name", "published_at", "html_url", "prerelease", "draft")} if release else None)
        ref = "repository:" + str(raw["id"])
        coverage = {"repository_metadata": True, "latest_published_release": True, "all_tags_or_code": False,
                    "code_executed": False, "latest_release_found": release is not None}
        evidence_rows = [evidence(ref, raw["html_url"], content, raw.get("description") or raw["full_name"], None, coverage)]
        facts = [fact("repository", raw["html_url"], ref), fact("description", raw.get("description"), ref),
                 fact("primary_language", raw.get("language"), ref), fact("license_spdx", content["license_spdx"], ref)]
        if release:
            release_ref = "release:" + str(release["id"])
            body = release.get("body") or release.get("name") or release["tag_name"]
            release_content = {key: release.get(key) for key in ("id", "tag_name", "name", "published_at", "html_url", "prerelease", "draft", "body")}
            # Bounded text, with upstream incompleteness explicitly retained.
            release_content["body"] = body[:7000]
            release_coverage = {"release_metadata": True, "body_truncated": len(body) > 7000, "code_executed": False}
            evidence_rows.append(evidence(release_ref, release["html_url"], release_content, body[:7000], release.get("published_at"), release_coverage))
            facts.append(fact("latest_release", release["tag_name"], release_ref))
        return {"source_id": "github", "scope_key": scope, "status": "ok", "coverage": coverage,
                "evidence": evidence_rows, "facts": facts}
    except SourceError as exc:
        return failed("github", scope, exc.reason, "not_found" if exc.status == 404 else "unavailable")
    except (KeyError, TypeError):
        return failed("github", scope, "invalid_upstream_schema")


def collect_opendart(corp_code, days=30):
    scope = "corp:" + str(corp_code) + ":rolling-days:" + str(days) + ":v1"
    key = os.getenv("OPENDART_API_KEY") or os.getenv("DART_API_KEY")
    if not key:
        return failed("opendart", scope, "OPENDART_API_KEY_required", "needs_credentials")
    if not re.fullmatch(r"[0-9]{8}", corp_code or ""):
        return failed("opendart", scope, "corp_code_required", "not_found")
    try:
        raw = read_json("https://opendart.fss.or.kr/api/company.json?" + urlencode({"crtfc_key": key, "corp_code": corp_code}))
        if raw.get("status") != "000":
            return failed("opendart", scope, "upstream_status_" + str(raw.get("status", "unknown")))
        ref = "company:" + corp_code
        company = {k: raw.get(k) for k in ("corp_code", "corp_name", "corp_name_eng", "stock_code", "ceo_nm", "corp_cls", "adres", "hm_url", "induty_code")}
        rows = [evidence(ref, "https://dart.fss.or.kr/dsae001/main.do?" + urlencode({"selectKey": corp_code}), company,
                         raw["corp_name"], coverage={"company_overview_only": True, "world_current_truth_verified": False})]
        facts = [fact("company_name", raw["corp_name"], ref), fact("reported_ceo", raw.get("ceo_nm"), ref), fact("reported_address", raw.get("adres"), ref)]
        until = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))).date()
        since = until - timedelta(days=days)
        listing = read_json("https://opendart.fss.or.kr/api/list.json?" + urlencode({"crtfc_key": key, "corp_code": corp_code,
                   "bgn_de": since.strftime("%Y%m%d"), "end_de": until.strftime("%Y%m%d"), "page_count": 10, "page_no": 1}))
        if listing.get("status") not in {"000", "013"}:
            return failed("opendart", scope, "upstream_status_" + str(listing.get("status", "unknown")))
        for report in listing.get("list", []):
            report_ref = "filing:" + report["rcept_no"]
            report_content = {k: report.get(k) for k in ("corp_code", "corp_name", "report_nm", "rcept_no", "rcept_dt", "flr_nm", "rm")}
            rows.append(evidence(report_ref, "https://dart.fss.or.kr/dsaf001/main.do?" + urlencode({"rcpNo": report["rcept_no"]}),
                                 report_content, report["report_nm"], report.get("rcept_dt"), {"filing_metadata_only": True, "date_precision": "day", "body_collected": False}))
            facts.append(fact("filing", report_content, report_ref))
        coverage = {"since": since.isoformat(), "until": until.isoformat(), "page": 1, "max_results": 10,
                    "total_count": listing.get("total_count", 0), "filing_bodies_collected": False,
                    "has_more": int(listing.get("total_page", 0) or 0) > 1, "missing_from_window_is_not_deletion": True}
        return {"source_id": "opendart", "scope_key": scope, "status": "ok", "coverage": coverage, "evidence": rows, "facts": facts}
    except SourceError as exc:
        return failed("opendart", scope, exc.reason)
    except (KeyError, TypeError, ValueError):
        return failed("opendart", scope, "invalid_upstream_schema")


def collect_naver(query):
    scope = "news:" + hashlib.sha256(query.encode()).hexdigest() + ":date:first5:v1"
    client_id, secret = os.getenv("NAVER_CLIENT_ID"), os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not secret:
        return failed("naver_news", scope, "NAVER_CLIENT_ID_and_NAVER_CLIENT_SECRET_required", "needs_credentials")
    try:
        raw = read_json("https://openapi.naver.com/v1/search/news.json?" + urlencode({"query": query, "display": 5, "start": 1, "sort": "date"}),
                        {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": secret})
        # Preserve an explicit search observation even when no articles match.
        search_ref = "search:" + hashlib.sha256(query.encode()).hexdigest()
        search_content = {"query": query, "total": raw.get("total"), "items": raw.get("items", [])}
        rows = [evidence(search_ref, "https://search.naver.com/search.naver?" + urlencode({"where": "news", "query": query}),
                         search_content, query, coverage={"search_metadata_only": True, "article_bodies_collected": False})]
        facts = []
        for article in raw.get("items", []):
            uri = article.get("originallink") or article["link"]
            article_ref = "article:" + hashlib.sha256(uri.encode()).hexdigest()
            content = {key: article.get(key) for key in ("title", "description", "originallink", "link", "pubDate")}
            rows.append(evidence(article_ref, uri, content, article.get("description") or article["title"], article.get("pubDate"),
                                 {"article_bodies_collected": False, "time_semantics": "provided_to_naver_or_origin"}))
            facts.append(fact("news_candidate", content, article_ref))
        coverage = {"max_results": 5, "total": raw.get("total"), "article_bodies_collected": False,
                    "has_more": int(raw.get("total", 0)) > len(raw.get("items", [])), "same_name_not_identity_proof": True}
        return {"source_id": "naver_news", "scope_key": scope, "status": "ok", "coverage": coverage, "evidence": rows, "facts": facts}
    except SourceError as exc:
        return failed("naver_news", scope, exc.reason)
    except (KeyError, TypeError, ValueError):
        return failed("naver_news", scope, "invalid_upstream_schema")
