import unittest

from scripts.archive_nse_ad_hoc_holiday_circulars import build_manifest, is_official_nse_url


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
            expected_count=2,
        )
        self.assertEqual(report["corroborating_records"], corroborating)
        self.assertEqual(report["archived_count"], 1)
        self.assertEqual(report["expected_count"], 2)
        self.assertEqual(report["independent_review_status"], "PENDING")
        self.assertEqual(report["calendar_completeness"], "NOT_CERTIFIED")
        self.assertEqual(report["research_status"], "RESEARCH_HOLD")
        self.assertFalse(report["holdout_access_authorized")


if __name__ == "__main__":
    unittest.main()
