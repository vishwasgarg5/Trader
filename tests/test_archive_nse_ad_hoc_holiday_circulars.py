import unittest
from unittest.mock import patch

from scripts.archive_nse_ad_hoc_holiday_circulars import (DownloadError, build_manifest, download, is_official_nse_url)


class OfficialNSEHostClassificationTests(unittest.TestCase):
    def test_accepts_exact_official_nse_hosts_over_https(self):
        for url in (
            "https://nsearchives.nseindia.com/content/circulars/CMTR57285.pdf",
            "https://archives.nseindia.com/content/circulars/CMTR57285.pdf",
            "https://www.nseindia.com/",
            "https://www.niftyindices.com/Press_Release/example.pdf",
        ):
            with self.subTest(url=url):
                self.assertTrue(is_official_nse_url(url))

    def test_rejects_lookalike_and_untrusted_hosts(self):
        for url in (
            "https://nseindia.com.evil.example/file.pdf",
            "https://evil-nseindia.com/file.pdf",
            "https://nseindia.com@evil.example/file.pdf",
            "https://geplcapital.com/file.pdf",
            "http://nsearchives.nseindia.com/file.pdf",
        ):
            with self.subTest(url=url):
                self.assertFalse(is_official_nse_url(url))


    def test_download_error_preserves_each_candidate_and_retry(self):
        with patch("scripts.archive_nse_ad_hoc_holiday_circulars.urllib.request.urlopen", side_effect=OSError("blocked")), patch("scripts.archive_nse_ad_hoc_holiday_circulars.time.sleep"):
            with self.assertRaises(DownloadError) as caught:
                download(["https://nsearchives.nseindia.com/a.pdf", "https://geplcapital.com/a.pdf"])
        self.assertEqual(len(caught.exception.attempts), 4)
        self.assertEqual([item["url"] for item in caught.exception.attempts], ["https://nsearchives.nseindia.com/a.pdf"] * 2 + ["https://geplcapital.com/a.pdf"] * 2)
        self.assertEqual([item["attempt"] for item in caught.exception.attempts], [1, 2, 1, 2])
    def test_manifest_records_corroboration_without_promoting_readiness(self):
        corroborating = [{
            "document_type": "OFFICIAL_NSE_INDICES_PRESS_RELEASE_CORROBORATION_NOT_CIRCULAR",
            "archive_path": "data/reference/source_documents/nse_ad_hoc_holiday_circulars/2023-06-27_NSE_Indices_press_release.pdf",
            "sha256": "a" * 64,
        }]
        report = build_manifest(
            records=[{"circular_reference": "NSE/CMTR/40536"}],
            failures=[{"circular_reference": "NSE/CMTR/57285"}],
            corroborating_records=corroborating,
            corroborating_failures=[],
            discovered_mirror_candidates=[{
                "related_circular_reference": "NSE/CMTR/57285",
                "discovery_status": "DISCOVERED_CONTENT_INDEXED_NOT_ARCHIVED",
                "sha256": None,
            }],
            expected_count=2,
        )
        self.assertEqual(report["corroborating_records"], corroborating)
        self.assertEqual(
            report["discovered_mirror_candidates"][0]["discovery_status"],
            "DISCOVERED_CONTENT_INDEXED_NOT_ARCHIVED",
        )
        self.assertIsNone(report["discovered_mirror_candidates"][0]["sha256"])
        self.assertEqual(report["archived_count"], 1)
        self.assertEqual(report["expected_count"], 2)
        self.assertEqual(report["independent_review_status"], "PENDING")
        self.assertEqual(report["calendar_completeness"], "NOT_CERTIFIED")
        self.assertEqual(report["research_status"], "RESEARCH_HOLD")
        self.assertFalse(report["holdout_access_authorized"])


if __name__ == "__main__":
    unittest.main()
