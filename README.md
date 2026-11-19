# ROFL archive

Private original replay archive, organized by season patch: `26.16/`, `26.17/`, etc.
Client header versions `16.xx` map to season patch `26.xx`. Directories are created when files arrive.

ROFL binaries use Git LFS. Clone with Git LFS installed (`git lfs pull`).
`manifest.json` records each original file's version, path, size and SHA-256.
Gzip-wrapped originals remain byte-identical; only their header is decompressed to classify them.

The host runs `python3 /home/ubuntu/rofl-archive/sync.py` every 10 minutes.
Source: `/var/lib/yummi-rofl/broadcast-replays`. Source files are never removed.
Unknown versions fail visibly instead of being guessed. Existing archives are retained.
GitHub LFS storage/bandwidth limits apply; failed pushes are retried on the next run.
