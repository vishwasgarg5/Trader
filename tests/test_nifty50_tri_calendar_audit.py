import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from trader.nifty50_tri_calendar_audit import audit


class Nifty50TRICalendarAuditTests(unittest.TestCase):
    def _write_tri(self, data: Path, rows: list[dict[str, str]], raw: Path) -> None:
        digest = hashlib.sha256(raw.read_bytes()).hexdigest()
        with data.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["session_date", "tri_close", "evidence_path", "evidence_sha256"],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    **row,
                    "evidence_path": str(raw),
                    "evidence_sha256": digest,
                })

    def test_reports_chronology_and_raw_hash_linkage_without_certifying_calendar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "chunk.json"
            raw.write_text('[{"Index Name":"NIFTY 50"}]', encoding="utf-8")
            data = root / "tri.csv"
            self._write_tri(data, [
                {"session_date": "2024-01-01", "tri_close": "100"},
                {"session_date": "2024-01-02", "tri_close": "101"},
            ], raw)

            report = audit(data)
            self.assertEqual(report["observation_count"], 2)
            self.assertEqual(report["raw_source_files_verified"], 1)
            self.assertEqual(report["chronology_and_hash_checks"], "PASS")
            self.assertEqual(report["calendar_completeness"], "NOT_CERTIFIED_NO_INDEPENDENT_EXCHANGE_CALENDAR")
            self.assertEqual(report["research_status"], "RESEARCH_HOLD")
            self.assertEqual(report["quarters_expected"], 28)
            self.assertEqual(report["quarters_with_observations"], 1)
            self.assertEqual(report["quarterly_observation_coverage"][24]["quarter"], "2024-Q1")
            self.assertEqual(report["quarterly_observation_coverage"][24]["observation_count"], 2)
            self.assertEqual(report["quarterly_observation_status"], "ONE_OR_MORE_QUARTERS_HAVE_NO_OBSERVATIONS")

    def test_rejects_duplicate_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "chunk.json"
            raw.write_text("{}", encoding="utf-8")
            data = root / "tri.csv"
            digest = hashlib.sha256(raw.read_bytes()).hexdigest()
            data.write_text(
                "session_date,tri_close,evidence_path,evidence_sha256\n"
                f"2024-01-01,100,{raw},{digest}\n"
                f"2024-01-01,101,{raw},{digest}\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate TRI session dates"):
                audit(data)

    def test_rejects_raw_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "chunk.json"
            raw.write_text("actual", encoding="utf-8")
            data = root / "tri.csv"
            data.write_text(
                "session_date,tri_close,evidence_path,evidence_sha256\n"
                f"2024-01-01,100,{raw},{'0' * 64}\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                audit(data)

    def test_emits_all_28_quarters_and_never_certifies_calendar_from_presence_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "chunk.json"
            raw.write_text("{}", encoding="utf-8")
            data = root / "tri.csv"
            rows = [
                {"session_date": f"{year}-{month:02d}-02", "tri_close": "100"}
                for year in range(2018, 2025)
                for month in (1, 4, 7, 10)
            ]
            self._write_tri(data, rows, raw)

            report = audit(data)
            self.assertEqual(report["quarters_expected"], 28)
            self.assertEqual(report["quarters_with_observations"], 28)
            self.assertEqual(report["quarterly_observation_status"], "OBSERVATIONS_PRESENT_IN_ALL_28_QUARTERS")
            self.assertEqual(
                [item["quarter"] for item in report["quarterly_observation_coverage"]],
                [f"{year}-Q{quarter}" for year in range(2018, 2025) for quarter in range(1, 5)],
            )
            self.assertEqual(report["calendar_completeness"], "NOT_CERTIFIED_NO_INDEPENDENT_EXCHANGE_CALENDAR")
            self.assertEqual(report["source_authenticity"], "PENDING_INDEPENDENT_REVIEW")
            self.assertEqual(report["research_status"], "RESEARCH_HOLD")


if __name__ == "__main__":
    unittest.main()
