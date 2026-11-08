"""Acquire official NSE Indices NIFTY 50 gross TRI, preserving raw responses."""
from __future__ import annotations
import csv, hashlib, json, math, sys, time, urllib.error, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE_PAGE="https://www.niftyindices.com/reports"
SOURCE_ENDPOINT="https://niftyindices.com/BackPage/getTotalReturnIndexString"
START_DATE=date(2018,1,1); END_DATE=date(2024,12,31)
USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 TraderResearch/1.0"
RAW_DIR=Path("data/reference/source_documents/nifty50_tri")
CSV_PATH=Path("data/reference/nifty50_tri.csv")
META_PATH=Path("data/reports/nifty50_tri_acquisition.json")
FIELDS=["session_date","tri_close","source_url","source_published_at","evidence_path","evidence_sha256","verification_status","reviewer","reviewed_at"]

def parse_date(v):
    for fmt in ("%d %b %Y","%d-%b-%Y","%d %B %Y","%Y-%m-%d","%d/%m/%Y"):
        try: return datetime.strptime(str(v).strip(),fmt).date()
        except ValueError: pass
    raise ValueError(f"unrecognized source date: {v!r}")

def field(row,names):
    d={str(k).strip().lower().replace("_","").replace(" ",""):v for k,v in row.items()}
    for n in names:
        k=n.lower().replace("_","").replace(" ","")
        if k in d: return d[k]
    return None

def parse_response(payload,start=START_DATE,end=END_DATE):
    try: outer=json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError,json.JSONDecodeError) as e:
        preview=payload[:180].decode("utf-8",errors="replace").replace("\\n"," ")
        raise ValueError(f"publisher response is not JSON; body preview={preview!r}") from e
    if isinstance(outer,list):
        rows=outer
    elif isinstance(outer,dict) and "d" in outer:
        inner=outer["d"]
        rows=json.loads(inner) if isinstance(inner,str) else inner
    else:
        raise ValueError("response is neither a JSON array nor an ASP.NET d payload")
    if rows is False or rows == "false": rows=[]
    if not isinstance(rows,list) or not rows: raise ValueError("official TRI response contains no observations")
    out=[]
    for i,r in enumerate(rows,1):
        if not isinstance(r,dict): raise ValueError(f"source row {i} is not an object")
        name=field(r,("indexName","Index Name","name"))
        if name is not None and str(name).strip().upper().replace(" ","")!="NIFTY50":
            raise ValueError(f"unexpected index identity in row {i}: {name!r}")
        dt=field(r,("HistoricalDate","Date","IndexDate"))
        val=field(r,("Total Returns Index","TotalReturnsIndex","TRI","triValue","TotalReturnIndexValue"))
        if dt is None or val is None: raise ValueError(f"source row {i} lacks date or Total Returns Index field")
        day=parse_date(dt); x=float(str(val).replace(",","").strip())
        if not math.isfinite(x) or x<=0: raise ValueError(f"invalid TRI value in row {i}")
        if start<=day<=end: out.append((day,x))
    if not out: raise ValueError(f"no TRI observations for {start}..{end}")
    out.sort()
    ds=[x[0] for x in out]
    if len(ds)!=len(set(ds)): raise ValueError("duplicate TRI session dates returned by official source")
    return out

def chunks():
    cur=START_DATE
    while cur<=END_DATE:
        boundary=date(cur.year,6,30) if cur.month<=6 else date(cur.year,12,31)
        stop=min(boundary,END_DATE)
        yield cur,stop
        cur=stop+timedelta(days=1)

def fetch_chunk(start,end):
    cinfo=f"{{'name':'NIFTY 50','startDate':'{start:%d-%b-%Y}','endDate':'{end:%d-%b-%Y}','indexName':'NIFTY 50'}}"
    req=urllib.request.Request(SOURCE_ENDPOINT,data=json.dumps({"cinfo":cinfo}).encode(),headers={
        "Content-Type":"application/json; charset=UTF-8","X-Requested-With":"XMLHttpRequest",
        "Referer":SOURCE_PAGE,"User-Agent":USER_AGENT,"Accept":"application/json, text/plain, */*",
        "Origin":"https://www.niftyindices.com"},method="POST")
    error=None
    for attempt in range(1,4):
        try:
            with urllib.request.urlopen(req,timeout=120) as resp:
                data=resp.read(20*1024*1024+1)
                if resp.status!=200: raise RuntimeError(f"HTTP {resp.status}")
                if len(data)>20*1024*1024: raise RuntimeError("response exceeds 20 MiB")
                return data
        except urllib.error.HTTPError as e:
            error=RuntimeError(f"HTTP {e.code}: {e.read(300).decode(errors='replace')}")
        except Exception as e: error=e
        if attempt<3: time.sleep(2*attempt)
    raise RuntimeError(f"request {start}..{end} failed: {error}")

def fetch():
    RAW_DIR.mkdir(parents=True,exist_ok=True)
    all_rows=[]; ev=[]
    for start,end in chunks():
        path=RAW_DIR/f"nifty50_tri_{start.isoformat()}_{end.isoformat()}.json"
        raw=fetch_chunk(start,end); path.write_bytes(raw)
        digest=hashlib.sha256(raw).hexdigest()
        rows=parse_response(raw,start,end); all_rows.extend(rows)
        ev.append({"requested_start":start.isoformat(),"requested_end":end.isoformat(),
                   "raw_response_path":path.as_posix(),"raw_response_bytes":len(raw),
                   "raw_response_sha256":digest,"record_count":len(rows),
                   "first_session":rows[0][0].isoformat(),"last_session":rows[-1][0].isoformat()})
    all_rows.sort(); ds=[r[0] for r in all_rows]
    if len(ds)!=len(set(ds)): raise ValueError("duplicate dates across TRI chunks")
    if not ds or ds[0]>START_DATE+timedelta(days=7) or ds[-1]<END_DATE-timedelta(days=7):
        raise ValueError(f"coverage does not span requested window: {ds[0] if ds else None}..{ds[-1] if ds else None}")
    return all_rows,ev

def main():
    now=datetime.now(timezone.utc)
    report={"experiment_id":"NIFTY50_PILOT_001","source_page":SOURCE_PAGE,"source_endpoint":SOURCE_ENDPOINT,
      "source_owner":"NSE Indices","index":"NIFTY 50","series":"Total Returns Index (gross TRI)",
      "explicitly_excluded_series":["Net Total Return Index","price-return index"],
      "requested_start":START_DATE.isoformat(),"requested_end":END_DATE.isoformat(),
      "retrieved_at_utc":now.isoformat(),"retrieved_at_ist":now.astimezone(ZoneInfo("Asia/Kolkata")).isoformat(),
      "status":"ACQUISITION_FAILED","independent_verification":"PENDING","reviewer":None,"holdout_access_authorized":False}
    try:
        rows,ev=fetch(); CSV_PATH.parent.mkdir(parents=True,exist_ok=True); META_PATH.parent.mkdir(parents=True,exist_ok=True)
        with CSV_PATH.open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader()
            for day,val in rows:
                e=next(x for x in ev if x["requested_start"]<=day.isoformat()<=x["requested_end"])
                w.writerow({"session_date":day.isoformat(),"tri_close":format(val,".10g"),
                  "source_url":SOURCE_ENDPOINT,"source_published_at":"","evidence_path":e["raw_response_path"],
                  "evidence_sha256":e["raw_response_sha256"],"verification_status":"ACQUIRED_PENDING_INDEPENDENT_REVIEW",
                  "reviewer":"","reviewed_at":""})
        report.update({"status":"ACQUIRED_PENDING_CALENDAR_AND_INDEPENDENT_REVIEW","record_count":len(rows),
          "first_session":rows[0][0].isoformat(),"last_session":rows[-1][0].isoformat(),"chunk_evidence":ev,
          "normalized_csv_path":CSV_PATH.as_posix(),"calendar_completeness":"NOT_YET_VERIFIED",
          "source_authenticity_review":"PENDING"})
    except Exception as e:
        report["error"]=f"{type(e).__name__}: {e}"
        META_PATH.parent.mkdir(parents=True,exist_ok=True)
        META_PATH.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps(report,indent=2,sort_keys=True)); return 1
    META_PATH.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True)); return 0

if __name__=="__main__": sys.exit(main())
