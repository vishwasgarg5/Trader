"""Reconcile the broad NSE archive inventory with the curated Nifty 50 notice register.

The report is diagnostic only: it never edits source rows, review states, or membership.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "data/reference/nifty50_annual_notice_inventory.csv"
REGISTER = ROOT / "data/reference/nifty50_notice_register.csv"
CATALOG = ROOT / "data/reference/nifty50_archive_discovery_catalog.csv"
REPORT = ROOT / "data/reports/nifty50_source_reconciliation.json"
DETAILS = ROOT / "data/reports/nifty50_source_reconciliation.csv"

INVENTORY_FIELDS = {
    "notice_id", "announcement_date", "source_url", "source_document_path",
    "source_sha256", "review_status",
}
REGISTER_FIELDS = {
    "notice_id", "publication_date", "source_url", "source_document_path",
    "source_sha256", "review_status",
}


def normalize_url(value: str) -> str:
    """Normalize host/default port/trailing slash while preserving path case."""
    value = (value or "").strip()
    if not value:
        return ""
    parts = urlsplit(value)
    scheme = (parts.scheme or "https").lower()
    host = (parts.hostname or "").lower()
    if parts.port and not ((scheme == "https" and parts.port == 443)
                           or (scheme == "http" and parts.port == 80)):
        host = f"{host}:{parts.port}"
    path = parts.path.rstrip("/") or "/"
    # Query strings and fragments are not part of the source document identity.
    return urlunsplit((scheme, host, path, "", ""))


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    """Read rows without crashing on ragged CSV; retain row-shape diagnostics."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing required columns: {sorted(missing)}")
        rows = []
        for row in reader:
            extras = row.pop(None, []) or []
            missing_values = [
                name for name in (reader.fieldnames or [])
                if row.get(name) is None
            ]
            cleaned = {
                key: (value.strip() if isinstance(value, str) else "")
                for key, value in row.items() if key is not None
            }
            cleaned["__csv_line_number__"] = str(reader.line_num)
            cleaned["__csv_extra_columns__"] = " | ".join(
                value.strip() for value in extras if isinstance(value, str)
            )
            cleaned["__csv_missing_columns__"] = ";".join(missing_values)
            rows.append(cleaned)
        return rows


def file_evidence(row: dict[str, str], root: Path) -> dict[str, str | bool]:
    relative = row.get("source_document_path", "")
    expected = row.get("source_sha256", "").lower()
    if not relative:
        return {
            "file_status": "PATH_NOT_RECORDED",
            "actual_sha256": "",
            "hash_status": "HASH_NOT_RECORDED" if not expected else "FILE_NOT_AVAILABLE",
        }
    path = root / relative
    if not path.is_file():
        return {
            "file_status": "FILE_NOT_FOUND",
            "actual_sha256": "",
            "hash_status": "FILE_NOT_AVAILABLE" if expected else "HASH_NOT_RECORDED",
        }
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if not expected:
        hash_status = "HASH_NOT_RECORDED"
    elif actual == expected:
        hash_status = "HASH_MATCH"
    else:
        hash_status = "HASH_MISMATCH"
    return {"file_status": "FILE_PRESENT", "actual_sha256": actual, "hash_status": hash_status}


def add_issue(issues: list[dict[str, str]], issue_type: str, source: str,
              notice_id: str, url: str, detail: str = "") -> None:
    issues.append({
        "issue_type": issue_type, "source": source, "notice_id": notice_id,
        "source_url": url, "detail": detail,
    })


def reconcile(inventory_path: Path = INVENTORY, register_path: Path = REGISTER,
              catalog_path: Path | None = CATALOG, report_path: Path = REPORT,
              details_path: Path = DETAILS, root: Path = ROOT) -> dict:
    inventory = read_csv(inventory_path, INVENTORY_FIELDS)
    register = read_csv(register_path, REGISTER_FIELDS)
    catalog = read_csv(catalog_path, {"source_url"}) if catalog_path and catalog_path.is_file() else []

    inventory_by_url: dict[str, list[dict[str, str]]] = defaultdict(list)
    register_by_url: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in inventory:
        key = normalize_url(row.get("source_url", ""))
        if key:
            inventory_by_url[key].append(row)
    for row in register:
        key = normalize_url(row.get("source_url", ""))
        if key:
            register_by_url[key].append(row)

    issues: list[dict[str, str]] = []
    detail_rows: list[dict[str, str]] = []
    for source_name, source_rows in (("inventory", inventory), ("register", register)):
        for row in source_rows:
            line_number = row.get("__csv_line_number__", "")
            if row.get("__csv_extra_columns__"):
                add_issue(
                    issues, "CSV_EXTRA_COLUMNS", source_name, row.get("notice_id", ""),
                    row.get("source_url", ""),
                    f"line={line_number}; extra={row['__csv_extra_columns__']}",
                )
            if row.get("__csv_missing_columns__"):
                add_issue(
                    issues, "CSV_MISSING_COLUMNS", source_name, row.get("notice_id", ""),
                    row.get("source_url", ""),
                    f"line={line_number}; missing={row['__csv_missing_columns__']}",
                )
    matched_register_rows = 0
    matched_inventory_ids: set[str] = set()
    ambiguous_matches = 0
    field_mismatches = defaultdict(int)
    file_status_counts = defaultdict(int)
    hash_status_counts = defaultdict(int)

    def evidence(source: str, row: dict[str, str]) -> dict[str, str | bool]:
        result = file_evidence(row, root)
        file_status_counts[str(result["file_status"])] += 1
        hash_status_counts[str(result["hash_status"])] += 1
        if result["file_status"] != "FILE_PRESENT":
            add_issue(issues, str(result["file_status"]), source,
                      row.get("notice_id", ""), row.get("source_url", ""),
                      row.get("source_document_path", ""))
        if result["hash_status"] in {"HASH_MISMATCH", "HASH_NOT_RECORDED"}:
            add_issue(issues, str(result["hash_status"]), source,
                      row.get("notice_id", ""), row.get("source_url", ""),
                      f"expected={row.get('source_sha256', '')}; actual={result['actual_sha256']}")
        return result

    inventory_evidence = {id(row): evidence("inventory", row) for row in inventory}
    register_evidence = {id(row): evidence("register", row) for row in register}

    for key, rows in inventory_by_url.items():
        if len(rows) > 1:
            add_issue(issues, "DUPLICATE_URL", "inventory", ";".join(r["notice_id"] for r in rows),
                      rows[0].get("source_url", ""), f"{len(rows)} inventory rows share normalized URL")
    for key, rows in register_by_url.items():
        if len(rows) > 1:
            add_issue(issues, "DUPLICATE_URL", "register", ";".join(r["notice_id"] for r in rows),
                      rows[0].get("source_url", ""), f"{len(rows)} register rows share normalized URL")

    for row in register:
        key = normalize_url(row.get("source_url", ""))
        matches = inventory_by_url.get(key, [])
        if not matches:
            # Notice IDs are different by design across these two ledgers; only
            # use ID matching as a guarded fallback when URL matching is absent.
            id_matches = [item for item in inventory if item.get("notice_id") == row.get("notice_id")]
            matches = id_matches
        if not matches:
            status = "REGISTER_ONLY"
            add_issue(issues, status, "register", row.get("notice_id", ""), row.get("source_url", ""),
                      f"review_status={row.get('review_status', '')}")
            if row.get("review_status") == "LOCATED_NOT_ARCHIVED":
                add_issue(issues, "LOCATED_BUT_NOT_ARCHIVED", "register",
                          row.get("notice_id", ""), row.get("source_url", ""),
                          "A source location is recorded, but no local PDF path or verified hash is recorded.")
            detail_rows.append({
                "reconciliation_status": status, "register_notice_id": row.get("notice_id", ""),
                "inventory_notice_ids": "", "source_url": row.get("source_url", ""),
                "path_register": row.get("source_document_path", ""), "path_inventory": "",
                "hash_register": row.get("source_sha256", ""), "hash_inventory": "",
                "field_mismatches": "none",
            })
            continue
        if len(matches) > 1:
            ambiguous_matches += 1
            add_issue(issues, "AMBIGUOUS_MATCH", "register", row.get("notice_id", ""),
                      row.get("source_url", ""), ";".join(x["notice_id"] for x in matches))
            continue

        matched_register_rows += 1
        inv = matches[0]
        matched_inventory_ids.add(inv.get("notice_id", ""))
        mismatches = []
        comparisons = (
            ("source_url", row.get("source_url", ""), inv.get("source_url", "")),
            ("source_document_path", row.get("source_document_path", ""), inv.get("source_document_path", "")),
            ("source_sha256", row.get("source_sha256", "").lower(), inv.get("source_sha256", "").lower()),
            ("publication_date", row.get("publication_date", ""), inv.get("announcement_date", "")),
        )
        for field, register_value, inventory_value in comparisons:
            if register_value and inventory_value and register_value != inventory_value:
                mismatches.append(field)
                field_mismatches[field] += 1
                add_issue(issues, f"{field.upper()}_MISMATCH", "register_vs_inventory",
                          row.get("notice_id", ""), row.get("source_url", ""),
                          f"register={register_value}; inventory={inventory_value}")
        status = "MATCHED" if not mismatches else "MATCHED_WITH_FIELD_MISMATCH"
        detail_rows.append({
            "reconciliation_status": status, "register_notice_id": row.get("notice_id", ""),
            "inventory_notice_ids": inv.get("notice_id", ""), "source_url": row.get("source_url", ""),
            "path_register": row.get("source_document_path", ""),
            "path_inventory": inv.get("source_document_path", ""),
            "hash_register": row.get("source_sha256", ""),
            "hash_inventory": inv.get("source_sha256", ""),
            "field_mismatches": ";".join(mismatches) or "none",
        })

    inventory_only = [row for row in inventory if row.get("notice_id", "") not in matched_inventory_ids]
    for row in inventory_only:
        # These are broad archive catalogue rows, not necessarily missing
        # register entries: the register is a curated Nifty 50 evidence ledger.
        detail_rows.append({
            "reconciliation_status": "INVENTORY_ONLY_CANDIDATE_OR_CONTROL",
            "register_notice_id": "", "inventory_notice_ids": row.get("notice_id", ""),
            "source_url": row.get("source_url", ""), "path_register": "",
            "path_inventory": row.get("source_document_path", ""),
            "hash_register": "", "hash_inventory": row.get("source_sha256", ""),
            "field_mismatches": "not_applicable_curated_register_subset",
        })

    catalog_urls = {normalize_url(row.get("source_url", "")) for row in catalog
                    if normalize_url(row.get("source_url", ""))}
    inventory_urls = set(inventory_by_url)
    catalog_only = sorted(catalog_urls - inventory_urls)
    inventory_not_in_catalog = sorted(inventory_urls - catalog_urls)
    for url in catalog_only:
        add_issue(issues, "CATALOG_ONLY_URL", "discovery_catalog", "", url,
                  "Discovery catalog row has no annual inventory URL match.")
    for url in inventory_not_in_catalog:
        add_issue(issues, "INVENTORY_ONLY_URL", "annual_inventory", "", url,
                  "Annual inventory URL has no discovery catalog URL match.")

    register_status_counts = defaultdict(int)
    for row in register:
        register_status_counts[row.get("review_status", "")] += 1

    report = {
        "inventory_rows": len(inventory),
        "register_rows": len(register),
        "discovery_catalog_rows": len(catalog),
        "inventory_unique_urls": len(inventory_urls),
        "register_unique_urls": len(register_by_url),
        "catalog_unique_urls": len(catalog_urls),
        "register_rows_matched_to_inventory": matched_register_rows,
        "register_rows_without_inventory_match": sum(
            1 for row in register if not inventory_by_url.get(normalize_url(row.get("source_url", "")))
            and not any(item.get("notice_id") == row.get("notice_id") for item in inventory)
        ),
        "inventory_rows_represented_in_register": len(matched_inventory_ids),
        "inventory_only_rows": len(inventory_only),
        "register_duplicate_url_groups": sum(1 for rows in register_by_url.values() if len(rows) > 1),
        "inventory_duplicate_url_groups": sum(1 for rows in inventory_by_url.values() if len(rows) > 1),
        "ambiguous_matches": ambiguous_matches,
        "catalog_only_unique_urls": len(catalog_only),
        "inventory_urls_absent_from_catalog": len(inventory_not_in_catalog),
        "register_review_status_counts": dict(sorted(register_status_counts.items())),
        "file_status_counts": dict(sorted(file_status_counts.items())),
        "hash_status_counts": dict(sorted(hash_status_counts.items())),
        "field_mismatch_counts": dict(sorted(field_mismatches.items())),
        "issues": issues,
        "details_csv": str(details_path.relative_to(root)) if details_path.is_relative_to(root) else str(details_path),
        "coverage_complete": False,
        "membership_written": False,
        "policy": (
            "The 684-row annual inventory is a broad archive candidate/control ledger; "
            "the notice register is a curated Nifty 50 evidence subset, so inventory-only "
            "rows are not automatically missing register entries. URL matching is canonical "
            "identity matching; duplicate register rows may represent distinct analytical roles "
            "for one source document. Hashes are verified against local file bytes when present. "
            "No source rows, review states, membership intervals, or model settings are changed."
        ),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    details_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "reconciliation_status", "register_notice_id", "inventory_notice_ids", "source_url",
        "path_register", "path_inventory", "hash_register", "hash_inventory", "field_mismatches",
    ]
    with details_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(detail_rows)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=INVENTORY)
    parser.add_argument("--register", type=Path, default=REGISTER)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--details", type=Path, default=DETAILS)
    args = parser.parse_args()
    report = reconcile(args.inventory, args.register, args.catalog, args.report, args.details)
    print(json.dumps({key: report[key] for key in (
        "inventory_rows", "register_rows", "discovery_catalog_rows",
        "register_rows_matched_to_inventory", "register_rows_without_inventory_match",
        "inventory_only_rows", "catalog_only_unique_urls", "inventory_urls_absent_from_catalog",
        "file_status_counts", "hash_status_counts", "field_mismatch_counts",
    )}, indent=2))


if __name__ == "__main__":
    main()
