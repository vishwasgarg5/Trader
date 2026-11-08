import json
import unittest
from datetime import date

from trader.nifty50_tri_acquisition import parse_response


class Nifty50TRIAcquisitionTests(unittest.TestCase):
    def test_parses_total_returns_index_not_net_tri(self):
        payload = json.dumps({
            "d": json.dumps([
                {
                    "indexName": "NIFTY 50",
                    "HistoricalDate": "31 Dec 2024",
                    "Total Returns Index": "42000.50",
                    "Net Total Return Index": "41900.25",
                },
                {
                    "indexName": "NIFTY 50",
                    "HistoricalDate": "01 Jan 2018",
                    "Total Returns Index": "15000.00",
                    "Net Total Return Index": "14900.00",
                },
            ])
        }).encode()
        rows = parse_response(payload)
        self.assertEqual(rows[0], (date(2018, 1, 1), 15000.0))
        self.assertEqual(rows[-1], (date(2024, 12, 31), 42000.5))

    def test_rejects_wrong_index(self):
        payload = json.dumps({"d": json.dumps([
            {"indexName": "NIFTY 500", "HistoricalDate": "31 Dec 2024",
             "Total Returns Index": "42000"}
        ])}).encode()
        with self.assertRaisesRegex(ValueError, "unexpected index identity"):
            parse_response(payload)

    def test_rejects_net_tri_only_payload(self):
        payload = json.dumps({"d": json.dumps([
            {"indexName": "NIFTY 50", "HistoricalDate": "31 Dec 2024",
             "Net Total Return Index": "42000"}
        ])}).encode()
        with self.assertRaisesRegex(ValueError, "lacks date or Total Returns Index"):
            parse_response(payload)

    def test_rejects_duplicate_dates(self):
        row = {"indexName": "NIFTY 50", "HistoricalDate": "31 Dec 2024",
               "Total Returns Index": "42000"}
        payload = json.dumps({"d": json.dumps([row, row])}).encode()
        with self.assertRaisesRegex(ValueError, "duplicate TRI session dates"):
            parse_response(payload)


if __name__ == "__main__":
    unittest.main()
