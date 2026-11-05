from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
import threading
import time

import pandas as pd
import requests

BASE_URL = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{date}.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "text/csv,application/octet-stream,*/*",
    "Referer": "https://www.nseindia.com/all-reports",
}
COLUMNS = ["date", "symbol", "delivery_pct"]
_thread_local = threading.local()


def _session() -> requests.Session:
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update(HEADERS)
        # NSE archive access can depend on a site session; use one per worker.
        try:
            session.get("https://www.nseindia.com", timeout=15)
        except requests.RequestException:
            pass
        _thread_local.session = session
    return session


def parse_full_bhavcopy(
    payload: bytes, expected_date: pd.Timestamp, symbols: set[str]
) -> pd.DataFrame:
    """Parse NSE's full bhavcopy and return delivery percentages for EQ stocks."""
    # NSE occasionally serves legacy-encoded CSVs; try UTF-8 (with BOM), then
    # Windows-1252 and Latin-1. Never decode with replacement characters.
    last_decode_error = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            raw = pd.read_csv(BytesIO(payload), encoding=encoding)
            break
        except UnicodeDecodeError as exc:
            last_decode_error = exc
    else:
        raise ValueError(f"Unable to decode NSE bhavcopy: {last_decode_error}")
    raw.columns = [str(column).strip().upper() for column in raw.columns]
    required = {"SYMBOL", "SERIES", "DATE1", "DELIV_PER"}
    missing = required.difference(raw.columns)
    if missing:
        raise ValueError(f"NSE full bhavcopy missing columns: {sorted(missing)}")

    raw["DATE1"] = pd.to_datetime(raw["DATE1"], dayfirst=True, errors="coerce")
    valid_dates = raw["DATE1"].dropna().dt.normalize().unique()
    expected = pd.Timestamp(expected_date).normalize()
    if len(valid_dates) != 1 or pd.Timestamp(valid_dates[0]) != expected:
        raise ValueError(
            f"NSE bhavcopy date mismatch: expected {expected.date()}, got {list(valid_dates)}"
        )

    raw["SYMBOL"] = raw["SYMBOL"].astype(str).str.strip().str.upper()
    raw["SERIES"] = raw["SERIES"].astype(str).str.strip().str.upper()
    raw["DELIV_PER"] = pd.to_numeric(raw["DELIV_PER"], errors="coerce")
    selected = raw.loc[
        raw["SERIES"].eq("EQ") & raw["SYMBOL"].isin(symbols),
        ["DATE1", "SYMBOL", "DELIV_PER"],
    ].copy()
    selected = selected.rename(columns={"DATE1": "date", "SYMBOL": "nse_symbol", "DELIV_PER": "delivery_pct"})
    selected["date"] = pd.to_datetime(selected["date"]).dt.normalize()
    selected["symbol"] = selected.pop("nse_symbol") + ".NS"
    selected.loc[~selected["delivery_pct"].between(0, 100), "delivery_pct"] = float("nan")
    selected = selected.dropna(subset=["delivery_pct"])
    if selected["symbol"].duplicated().any():
        raise ValueError("NSE full bhavcopy contains duplicate EQ symbol rows")
    return selected[COLUMNS].reset_index(drop=True)


def _fetch_one(day: pd.Timestamp, symbols: set[str]) -> tuple[str, pd.DataFrame]:
    day = pd.Timestamp(day).normalize()
    url = BASE_URL.format(date=day.strftime("%d%m%Y"))
    session = _session()
    for attempt in range(3):
        response = session.get(url, timeout=30)
        if response.status_code == 404:
            return "not_found", pd.DataFrame(columns=COLUMNS)
        if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
            time.sleep(2 ** attempt)
            continue
        response.raise_for_status()
        try:
            rows = parse_full_bhavcopy(response.content, day, symbols)
        except ValueError as exc:
            # The archive can occasionally return an adjacent session's file
            # for a requested date. Record it as a gap, not as valid data and
            # not as an infrastructure failure that aborts the whole study.
            if "date mismatch" in str(exc):
                return "date_mismatch", pd.DataFrame(columns=COLUMNS)
            raise
        return "downloaded", rows
    raise RuntimeError(f"Unable to download NSE bhavcopy for {day.date()}")


def download_delivery_history(
    prices: dict[str, pd.DataFrame],
    output_path: Path,
    workers: int = 6,
) -> dict:
    """Backfill/cache daily NSE delivery percentages for the supplied universe.

    The official daily full-bhavcopy report contains deliverable quantity and
    delivery percentage. Downloaded dates (including 404s) are logged so future
    runs fetch only dates not previously checked.
    """
    symbols = {str(symbol).removesuffix(".NS").strip().upper()
               for symbol in prices if not str(symbol).startswith("^")}
    if not symbols:
        raise ValueError("No NSE equity symbols supplied for delivery backfill")
    dates = sorted({
        pd.Timestamp(day).tz_localize(None).normalize()
        for symbol, frame in prices.items() if not symbol.startswith("^")
        for day in frame.index
    })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = output_path.with_name("delivery_download_log.csv")
    log = (
        pd.read_csv(log_path, parse_dates=["date"])
        if log_path.exists() else pd.DataFrame(columns=["date", "status", "rows"])
    )
    checked = set(pd.to_datetime(log["date"]).dt.normalize()) if not log.empty else set()
    if output_path.exists():
        existing = pd.read_csv(output_path, parse_dates=["date"])
        if not existing.empty:
            checked.update(pd.to_datetime(existing["date"]).dt.normalize())
    pending = [day for day in dates if day not in checked]

    new_rows = []
    new_log = []
    failures = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_one, day, symbols): day for day in pending}
        for future in as_completed(futures):
            day = futures[future]
            try:
                status, rows = future.result()
                new_log.append({"date": day, "status": status, "rows": len(rows)})
                if not rows.empty:
                    new_rows.append(rows)
            except Exception as exc:
                failures.append(f"{day.date()}: {type(exc).__name__}: {exc}")

    if failures:
        raise RuntimeError(
            "NSE delivery download incomplete; no coverage log was updated. "
            + "; ".join(failures[:10])
        )
    if new_rows:
        combined_rows = pd.concat(new_rows, ignore_index=True)
        if output_path.exists():
            old_rows = pd.read_csv(output_path, parse_dates=["date"])
            combined_rows = pd.concat([old_rows, combined_rows], ignore_index=True)
        combined_rows["date"] = pd.to_datetime(combined_rows["date"]).dt.normalize()
        combined_rows = combined_rows.drop_duplicates(["date", "symbol"], keep="last")
        combined_rows.sort_values(["date", "symbol"]).to_csv(output_path, index=False)

    if new_log:
        log = pd.concat([log, pd.DataFrame(new_log)], ignore_index=True)
        log["date"] = pd.to_datetime(log["date"]).dt.normalize()
        log = log.drop_duplicates(["date"], keep="last").sort_values("date")
        log.to_csv(log_path, index=False)

    all_rows = pd.read_csv(output_path) if output_path.exists() else pd.DataFrame(columns=COLUMNS)
    return {
        "requested_trading_dates": len(dates),
        "newly_checked_dates": len(pending),
        "downloaded_dates": int((pd.DataFrame(new_log).get("status", pd.Series(dtype=str)) == "downloaded").sum()),
        "not_found_dates": int((pd.DataFrame(new_log).get("status", pd.Series(dtype=str)) == "not_found").sum()),
        "delivery_rows_total": int(len(all_rows)),
        "delivery_symbols_total": int(all_rows["symbol"].nunique()) if not all_rows.empty else 0,
        "delivery_file": str(output_path),
        "source": "NSE full bhavcopy sec_bhavdata_full",
    }
