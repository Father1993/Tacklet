"""No-network regression tests for release asset validation."""

import hashlib
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from sticky.updater import UpdateError, checksum_for, is_newer, select_assets, verify_checksum


class UpdaterTests(unittest.TestCase):
    def test_selects_only_package_and_checksum_manifest(self):
        package, manifest = select_assets({'assets': [
            {'name': 'tacklet_0.2.0-1_all.deb', 'browser_download_url': 'package'},
            {'name': 'SHA256SUMS', 'browser_download_url': 'checksums'},
        ]})
        self.assertEqual(package['name'], 'tacklet_0.2.0-1_all.deb')
        self.assertEqual(manifest['name'], 'SHA256SUMS')

    def test_rejects_ambiguous_release_assets(self):
        with self.assertRaises(UpdateError):
            select_assets({'assets': [
                {'name': 'tacklet_0.2.0-1_all.deb'},
                {'name': 'tacklet_0.2.1-1_all.deb'},
                {'name': 'SHA256SUMS'},
            ]})

    def test_checksum_must_match_downloaded_package(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tacklet_0.2.0-1_all.deb'
            path.write_bytes(b'known package')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(checksum_for(f'{digest}  {path.name}\n', path.name), digest)
            verify_checksum(path, digest)
            with self.assertRaises(UpdateError):
                verify_checksum(path, '0' * 64)

    def test_downgrade_or_equal_version_is_rejected(self):
        with patch('sticky.updater.subprocess.run') as run:
            run.return_value.returncode = 1
            self.assertFalse(is_newer('0.2.0-1', '0.2.0-1'))
            run.assert_called_once_with(['dpkg', '--compare-versions', '0.2.0-1', 'gt', '0.2.0-1'])
