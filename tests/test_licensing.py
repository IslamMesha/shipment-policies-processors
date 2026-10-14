import base64
import unittest
from datetime import date

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from services.licensing import (
    LicenseError,
    canonical_payload,
    validate_license_data,
)


class LicenseValidationTests(unittest.TestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        public_key = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_key_b64 = base64.b64encode(public_key).decode("ascii")
        self.payload = {
            "version": 1,
            "license_id": "test-license",
            "customer": "Test Customer",
            "device_id": "device-123",
            "expires_on": "2027-01-01",
        }

    def signed_license(self, payload=None):
        signed_payload = dict(payload if payload is not None else self.payload)
        signature = self.private_key.sign(canonical_payload(signed_payload))
        return {
            "payload": signed_payload,
            "signature": base64.b64encode(signature).decode("ascii"),
        }

    def validate(self, license_data, **kwargs):
        return validate_license_data(
            license_data,
            public_key_b64=self.public_key_b64,
            device_id="device-123",
            **kwargs,
        )

    def test_accepts_valid_license_on_bound_machine(self):
        result = self.validate(
            self.signed_license(),
            today=date(2026, 12, 31),
        )
        self.assertEqual(result["license_id"], "test-license")

    def test_accepts_license_on_expiration_date(self):
        self.validate(
            self.signed_license(),
            today=date(2027, 1, 1),
        )

    def test_rejects_expired_license(self):
        with self.assertRaisesRegex(LicenseError, "expired"):
            self.validate(
                self.signed_license(),
                today=date(2027, 1, 2),
            )

    def test_rejects_license_for_another_machine(self):
        with self.assertRaisesRegex(LicenseError, "different computer"):
            validate_license_data(
                self.signed_license(),
                public_key_b64=self.public_key_b64,
                device_id="other-device",
                today=date(2026, 12, 31),
            )

    def test_rejects_modified_payload(self):
        license_data = self.signed_license()
        license_data["payload"]["customer"] = "Changed Customer"
        with self.assertRaisesRegex(LicenseError, "signature is invalid"):
            self.validate(license_data)

    def test_rejects_invalid_signature(self):
        license_data = self.signed_license()
        license_data["signature"] = base64.b64encode(b"invalid").decode("ascii")
        with self.assertRaisesRegex(LicenseError, "signature is invalid"):
            self.validate(license_data)

    def test_accepts_perpetual_license(self):
        payload = dict(self.payload, expires_on=None)
        self.validate(
            self.signed_license(payload),
            today=date(2099, 1, 1),
        )

    def test_rejects_invalid_expiration_date(self):
        payload = dict(self.payload, expires_on="2027-02-30")
        with self.assertRaisesRegex(LicenseError, "expiration date is invalid"):
            self.validate(self.signed_license(payload))

    def test_rejects_malformed_license_structure(self):
        with self.assertRaisesRegex(LicenseError, "invalid structure"):
            self.validate({"payload": self.payload})


if __name__ == "__main__":
    unittest.main()
