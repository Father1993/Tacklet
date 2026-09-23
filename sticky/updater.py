"""Verified updater for the Debian package published on GitHub Releases."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen


RELEASE_URL = 'https://api.github.com/repos/Father1993/Tacklet/releases/latest'
ASSET_RE = re.compile(r'^tacklet_[A-Za-z0-9.+:~\-]+_all\.deb$')


class UpdateError(RuntimeError):
    """A safe, human-readable reason why an update cannot continue."""


def select_assets(release: dict) -> tuple[dict, dict]:
    """Return exactly one Tacklet package and its checksum manifest."""
    assets = release.get('assets')
    if not isinstance(assets, list):
        raise UpdateError('GitHub response has no release assets.')
    packages = [asset for asset in assets
                if isinstance(asset, dict) and ASSET_RE.fullmatch(str(asset.get('name', '')))]
    checksums = [asset for asset in assets
                 if isinstance(asset, dict) and asset.get('name') == 'SHA256SUMS']
    if len(packages) != 1 or len(checksums) != 1:
        raise UpdateError('Latest release must contain exactly one Tacklet .deb and SHA256SUMS.')
    return packages[0], checksums[0]


def checksum_for(manifest: str, filename: str) -> str:
    for line in manifest.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip('*') == filename:
            digest = parts[0].lower()
            if re.fullmatch(r'[0-9a-f]{64}', digest):
                return digest
    raise UpdateError(f'SHA256SUMS has no valid checksum for {filename}.')


def verify_checksum(path: Path, expected: str) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise UpdateError('Downloaded package checksum does not match SHA256SUMS; nothing was installed.')


def installed_version() -> str:
    result = subprocess.run(
        ['dpkg-query', '-W', '-f=${Status} ${Version}', 'tacklet'],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.startswith('install ok installed '):
        raise UpdateError(
            'Tacklet is not installed as a Debian package. Remove the old source install with '
            './uninstall.sh, then install the .deb from GitHub Releases.')
    return result.stdout.removeprefix('install ok installed ').strip()


def is_newer(candidate: str, current: str) -> bool:
    result = subprocess.run(['dpkg', '--compare-versions', candidate, 'gt', current])
    if result.returncode not in (0, 1):
        raise UpdateError(f'Cannot compare Debian versions: {candidate!r} and {current!r}.')
    return result.returncode == 0


def _download(url: str, destination: Path, binary: bool) -> str | None:
    request = Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Tacklet-updater'})
    try:
        with urlopen(request, timeout=30) as response:
            data = response.read()
    except OSError as exc:
        raise UpdateError(f'Could not download release asset: {exc}') from exc
    destination.write_bytes(data)
    return None


def _latest_release() -> dict:
    request = Request(RELEASE_URL, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Tacklet-updater'})
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError(f'Could not read the latest GitHub release: {exc}') from exc


def update() -> int:
    if shutil.which('sudo') is None or shutil.which('apt') is None:
        raise UpdateError('This updater requires sudo and apt on Ubuntu or Debian.')
    current = installed_version()
    package, checksums = select_assets(_latest_release())
    package_name = str(package['name'])
    candidate = package_name.removeprefix('tacklet_').removesuffix('_all.deb')
    if not is_newer(candidate, current):
        print(f'Tacklet {current} is already up to date.')
        return 0
    if not package.get('browser_download_url') or not checksums.get('browser_download_url'):
        raise UpdateError('Release asset URL is missing.')

    with tempfile.TemporaryDirectory(prefix='tacklet-update-') as directory:
        directory_path = Path(directory)
        package_path = directory_path / package_name
        checksums_path = directory_path / 'SHA256SUMS'
        _download(str(checksums['browser_download_url']), checksums_path, binary=False)
        _download(str(package['browser_download_url']), package_path, binary=True)
        verify_checksum(package_path, checksum_for(checksums_path.read_text(encoding='utf-8'), package_name))
        result = subprocess.run(['sudo', 'apt', 'install', '--yes', str(package_path)])
        if result.returncode != 0:
            raise UpdateError('apt could not install the verified package.')
    print(f'Tacklet updated from {current} to {candidate}.')
    return 0


def main() -> int:
    try:
        return update()
    except UpdateError as exc:
        print(f'Tacklet update: {exc}', file=sys.stderr)
        return 1
