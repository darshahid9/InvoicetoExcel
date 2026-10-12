import unittest
from app import extract_invoice_fields, parse_amount

SAMPLE = """
ABC Traders
TAX INVOICE
Invoice No: ABC/2026/105
Invoice Date: 12/10/2026
GSTIN: 07ABCDE1234F1Z5
Place of Supply: Delhi
Taxable Value: 1,000.00
CGST 9% 90.00
SGST 9% 90.00
Grand Total: 1,180.00
"""

class InvoiceExtractionTests(unittest.TestCase):
    def test_amount_parser(self):
        self.assertEqual(parse_amount("1,180.00"), 1180.00)
        self.assertEqual(parse_amount("₹ 99.50"), 99.50)
        self.assertIsNone(parse_amount("not a number"))

    def test_common_invoice_fields(self):
        result = extract_invoice_fields(SAMPLE, "sample.pdf")
        self.assertEqual(result["source_file"], "sample.pdf")
        self.assertEqual(result["supplier_name"], "ABC Traders")
        self.assertEqual(result["invoice_number"], "ABC/2026/105")
        self.assertEqual(result["invoice_date"], "12/10/2026")
        self.assertEqual(result["gstin"], "07ABCDE1234F1Z5")
        self.assertEqual(result["subtotal"], 1000.00)
        self.assertEqual(result["cgst"], 90.00)
        self.assertEqual(result["sgst"], 90.00)
        self.assertEqual(result["total_amount"], 1180.00)

if __name__ == "__main__":
    unittest.main()
