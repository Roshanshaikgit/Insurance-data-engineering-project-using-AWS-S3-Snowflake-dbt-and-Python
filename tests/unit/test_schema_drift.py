
import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_schema_drift import validate_schema


class TestSchemaDrift(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.csv_path = self.root / "test_data.csv"
        self.contract_path = self.root / "test_contract.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_contract(self, columns):
        contract = {
            "required_columns": columns,
            "rules": {
                "allow_unexpected_columns": False
            }
        }
        self.contract_path.write_text(
            json.dumps(contract),
            encoding="utf-8"
        )

    def test_valid_schema_is_accepted(self):
        self.csv_path.write_text(
            "policyholder_id,full_name,city\n"
            "PH001,Aarav,Hyderabad\n",
            encoding="utf-8"
        )
        self.create_contract(
            ["policyholder_id", "full_name", "city"]
        )

        errors = validate_schema(
            self.csv_path, self.contract_path
        )

        self.assertEqual(errors, [])

    def test_missing_required_column_is_detected(self):
        self.csv_path.write_text(
            "policyholder_id,city\n"
            "PH001,Hyderabad\n",
            encoding="utf-8"
        )
        self.create_contract(
            ["policyholder_id", "full_name", "city"]
        )

        errors = validate_schema(
            self.csv_path, self.contract_path
        )

        self.assertTrue(
            any("Missing required columns" in error for error in errors)
        )

    def test_unexpected_column_is_detected(self):
        self.csv_path.write_text(
            "policyholder_id,full_name,city,extra_field\n"
            "PH001,Aarav,Hyderabad,test\n",
            encoding="utf-8"
        )
        self.create_contract(
            ["policyholder_id", "full_name", "city"]
        )

        errors = validate_schema(
            self.csv_path, self.contract_path
        )

        self.assertTrue(
            any("Unexpected columns" in error for error in errors)

        )
   
    def test_invalid_number_is_detected(self):
        self.csv_path.write_text(
            "claim_id,claim_amount\nCL001,ABC\n",
            encoding="utf-8"
        )
        self.contract_path.write_text(
            json.dumps({
                "required_columns": ["claim_id", "claim_amount"],
                "columns": {
                    "claim_id": "string",
                    "claim_amount": "number"
                },
                "rules": {"allow_unexpected_columns": False}
            }),
            encoding="utf-8"
        )

        errors = validate_schema(
            self.csv_path, self.contract_path
        )

        self.assertTrue(
            any("Invalid number values" in error for error in errors)
        )

    def test_invalid_date_is_detected(self):
        self.csv_path.write_text(
            "claim_id,claim_date\nCL001,not-a-date\n",
            encoding="utf-8"
        )
        self.contract_path.write_text(
            json.dumps({
                "required_columns": ["claim_id", "claim_date"],
                "columns": {
                    "claim_id": "string",
                    "claim_date": "date"
                },
                "rules": {"allow_unexpected_columns": False}
            }),
            encoding="utf-8"
        )

        errors = validate_schema(
            self.csv_path, self.contract_path
        )

        self.assertTrue(
            any("Invalid date values" in error for error in errors)
        )

    def test_blank_business_key_is_detected(self):
        self.csv_path.write_text(
            "policyholder_id,full_name\n"
            ",Aarav\n",
            encoding="utf-8"
        )
        self.contract_path.write_text(
            json.dumps({
                "required_columns": [
                    "policyholder_id",
                    "full_name"
                ],
                "columns": {
                    "policyholder_id": "string",
                    "full_name": "string"
                },
                "business_key": ["policyholder_id"],
                "rules": {
                    "allow_unexpected_columns": False,
                    "business_key_not_null": True,
                    "business_key_unique_within_batch": True
                }
            }),
            encoding="utf-8"
        )

        errors = validate_schema(
            self.csv_path, self.contract_path
        )

        self.assertTrue(
            any("Blank business key values" in error for error in errors)
        )

    def test_duplicate_business_key_is_detected(self):
        self.csv_path.write_text(
            "policyholder_id,full_name\n"
            "PH001,Aarav\n"
            "PH001,Maya\n",
            encoding="utf-8"
        )
        self.contract_path.write_text(
            json.dumps({
                "required_columns": [
                    "policyholder_id",
                    "full_name"
                ],
                "columns": {
                    "policyholder_id": "string",
                    "full_name": "string"
                },
                "business_key": ["policyholder_id"],
                "rules": {
                    "allow_unexpected_columns": False,
                    "business_key_not_null": True,
                    "business_key_unique_within_batch": True
                }
            }),
            encoding="utf-8"
        )

        errors = validate_schema(
            self.csv_path, self.contract_path
        )

        self.assertTrue(
            any("Duplicate business key values" in error
                for error in errors)
        )



if __name__ == "__main__":
    unittest.main()
