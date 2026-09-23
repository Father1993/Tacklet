"""Headless checks for the human-readable runtime diagnostics."""

import unittest

from sticky.diagnostics import Check, format_report, has_blocking_failure


class DiagnosticsTests(unittest.TestCase):
    def test_required_failure_is_blocking(self):
        checks = [Check('GTK', False, True, 'missing'), Check('tray', False, False, 'optional')]
        self.assertTrue(has_blocking_failure(checks))

    def test_optional_failure_is_not_blocking(self):
        checks = [Check('tray', False, False, 'optional')]
        self.assertFalse(has_blocking_failure(checks))

    def test_report_marks_error_and_optional_information(self):
        report = format_report([
            Check('GTK', False, True, 'install package'),
            Check('tray', False, False, 'enable extension'),
        ])
        self.assertIn('[ERROR] GTK: install package', report)
        self.assertIn('[INFO] tray: enable extension', report)
