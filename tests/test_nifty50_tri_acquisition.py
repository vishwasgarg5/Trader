import json, unittest
from datetime import date
from trader.nifty50_tri_acquisition import parse_response

class Nifty50TRIAcquisitionTests(unittest.TestCase):
    def test_publisher_schema_and_gross_tri(self):
        p=json.dumps({"d":json.dumps([
          {"Index Name":"Nifty 50","Date":"31 Dec 2024","TotalReturnsIndex":"42000.50","NTR_Value":"41900.25"},
          {"Index Name":"Nifty 50","Date":"01 Jan 2018","TotalReturnsIndex":"15000.00","NTR_Value":"14900.00"}])}).encode()
        r=parse_response(p)
        self.assertEqual(r[0],(date(2018,1,1),15000.0)); self.assertEqual(r[-1],(date(2024,12,31),42000.5))
    def test_wrong_index_rejected(self):
        p=json.dumps({"d":json.dumps([{"Index Name":"Nifty 500","Date":"31 Dec 2024","TotalReturnsIndex":"42000"}])}).encode()
        with self.assertRaisesRegex(ValueError,"unexpected index identity"): parse_response(p)
    def test_net_tri_only_rejected(self):
        p=json.dumps({"d":json.dumps([{"Index Name":"Nifty 50","Date":"31 Dec 2024","NTR_Value":"42000"}])}).encode()
        with self.assertRaisesRegex(ValueError,"lacks date or Total Returns Index"): parse_response(p)
    def test_duplicate_dates_rejected(self):
        row={"Index Name":"Nifty 50","Date":"31 Dec 2024","TotalReturnsIndex":"42000"}
        p=json.dumps({"d":json.dumps([row,row])}).encode()
        with self.assertRaisesRegex(ValueError,"duplicate TRI session dates"): parse_response(p)
    def test_non_json_diagnostic(self):
        with self.assertRaisesRegex(ValueError,"publisher response is not JSON"): parse_response(b"<html>Access denied</html>")

if __name__=="__main__": unittest.main()
