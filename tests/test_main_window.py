import unittest
from datetime import date

from main import format_license_status


class LicenseStatusDisplayTests(unittest.TestCase):
    def test_displays_expiry_date_and_days_remaining(self):
        status = format_license_status(
            date(2027, 1, 3),
            today=date(2027, 1, 1),
        )

        self.assertEqual(
            status,
            "License expiry: 2027-01-03 | Days remaining: 2 days",
        )

    def test_displays_singular_day_remaining(self):
        status = format_license_status(
            date(2027, 1, 2),
            today=date(2027, 1, 1),
        )

        self.assertEqual(
            status,
            "License expiry: 2027-01-02 | Days remaining: 1 day",
        )

    def test_displays_zero_days_on_expiry_date(self):
        status = format_license_status(
            date(2027, 1, 1),
            today=date(2027, 1, 1),
        )

        self.assertEqual(
            status,
            "License expiry: 2027-01-01 | Days remaining: 0 days",
        )

    def test_displays_expired_status_after_expiry_date(self):
        status = format_license_status(
            date(2026, 12, 31),
            today=date(2027, 1, 1),
        )

        self.assertEqual(status, "License expired on 2026-12-31")

    def test_displays_perpetual_license_status(self):
        self.assertEqual(
            format_license_status(None),
            "License expiry: Never | Days remaining: Unlimited",
        )


if __name__ == "__main__":
    unittest.main()
