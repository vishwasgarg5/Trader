import unittest

from scripts.archive_nse_ad_hoc_holiday_circulars import is_official_nse_url


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


if __name__ == "__main__":
    unittest.main()
