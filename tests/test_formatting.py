import unittest

from core.formatting import format_hours_minutes, format_ms, format_seconds


class FormattingTestCase(unittest.TestCase):
    def test_format_ms_and_seconds(self):
        self.assertEqual(format_ms(0), "0:00")
        self.assertEqual(format_ms(187_500), "3:07")
        self.assertEqual(format_seconds(65), "1:05")
        self.assertEqual(format_seconds(3600), "60:00")

    def test_format_hours_minutes(self):
        self.assertEqual(format_hours_minutes(0), "0 мин")
        self.assertEqual(format_hours_minutes(45), "45 сек")
        self.assertEqual(format_hours_minutes(15 * 60 + 20), "15 мин")
        self.assertEqual(format_hours_minutes(2 * 3600 + 15 * 60), "2 ч 15 мин")


if __name__ == "__main__":
    unittest.main()
