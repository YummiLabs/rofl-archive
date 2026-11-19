#!/usr/bin/env python3
"""Append original replay files to the private patch archive; never delete sources."""
import collections
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/var/lib/yummi-rofl/broadcast-replays')

def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    lock = (ROOT / '.git/archive-sync.lock').open('w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    index_path = ROOT / 'manifest.json'
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    errors = []
    for source in sorted(SOURCE.glob('*.rofl')):
        try:
            before = source.stat()
        except OSError as exc:
            errors.append(f'{source.name}: {exc}')
            continue
        previous = index.get(source.name)
        if previous and previous['size'] == before.st_size and previous['mtime_ns'] == before.st_mtime_ns:
            continue
        try:
            with source.open('rb') as stream:
                compressed = stream.read(2) == b'\x1f\x8b'
            with (gzip.open(source, 'rb') if compressed else source.open('rb')) as stream:
                header = stream.read(4096)
            if not header.startswith(b'RIOT'):
                raise ValueError('not a RIOT replay')
            match = re.search(rb'(\d{2})\.(\d{1,2})\.\d{3,6}\.\d{3,6}', header)
            if not match:
                raise ValueError('missing game version')
            version = match.group().decode()
            major, minor = map(int, version.split('.')[:2])
            patch = f'{major + 10 if major < 26 else major}.{minor}'
            sha = digest(source)
            target = ROOT / patch / source.name
            if target.exists() and digest(target) != sha:
                target = target.with_name(f'{source.stem}-{sha[:12]}.rofl')
            target.parent.mkdir(exist_ok=True)
            if not target.exists():
                temp = target.with_suffix('.tmp')
                shutil.copyfile(source, temp)
                after = source.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or digest(temp) != sha:
                    temp.unlink()
                    raise ValueError('source changed during copy')
                os.replace(temp, target)
            index[source.name] = dict(path=str(target.relative_to(ROOT)), version=version, sha256=sha, size=before.st_size, mtime_ns=before.st_mtime_ns)
        except Exception as exc:
            errors.append(f'{source.name}: {exc}')
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + '\n')
    git('add', '--all')
    if git('diff', '--cached', '--name-only'):
        git('commit', '-m', 'Archive replays by patch version')
    # Retry pending uploads even when there are no new files.
    git('push', '-u', 'origin', 'main')
    print(json.dumps(dict(files=len(index), patches=dict(collections.Counter(x['path'].split('/')[0] for x in index.values())), errors=errors)), flush=True)
    if errors:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
