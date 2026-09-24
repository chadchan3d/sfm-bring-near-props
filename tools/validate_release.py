#!/usr/bin/env python3
"""Validate the surviving SFM Bring Near: Props v1.0.1 release archive.

This is repository/publication tooling, not an SFM runtime test.
"""
from __future__ import print_function

import hashlib
import os
import sys
import zipfile
from pathlib import Path, PurePosixPath

EXPECTED_ZIP_NAME = "SFM_Bring_Near_Props_v1_01.zip"
EXPECTED_ZIP_SIZE = 40157
EXPECTED_ZIP_SHA256 = "2c598753595d6c15a8de8a6f043b86c98185b51df52841abdbe2a8ad0528716a"

EXPECTED_FILES = {
    "README.txt": {
        "size": 3687,
        "sha256": "030ba67e352059fb68c1e5fd4915f697b415f9a658c5b871af9c2853d2da8933",
        "repo": "README.txt",
    },
    "workshop/scripts/sfm/animset/SFM_Bring_Near_Props.py": {
        "size": 192833,
        "sha256": "f8f249920101f4fe17df2c773c15c0dad9ab962fa37fa65ba7368c15729a72c1",
        "repo": "workshop/scripts/sfm/animset/SFM_Bring_Near_Props.py",
    },
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(message):
    raise SystemExit("FAIL: " + message)


def safe_member(name):
    normalized = name.replace("\\", "/")
    p = PurePosixPath(normalized)
    if p.is_absolute():
        return False
    if any(part == ".." for part in p.parts):
        return False
    if len(normalized) >= 2 and normalized[1] == ":":
        return False
    return True


def main():
    if len(sys.argv) != 2:
        print("Usage: python tools/validate_release.py path/to/%s" % EXPECTED_ZIP_NAME)
        return 2

    archive_path = Path(sys.argv[1]).resolve()
    repo_root = Path(__file__).resolve().parent.parent

    if not archive_path.is_file():
        fail("archive not found: %s" % archive_path)

    if archive_path.name not in (EXPECTED_ZIP_NAME, "SFM_Bring_Near_Props_v1_01(1).zip"):
        fail("unexpected archive filename: %s" % archive_path.name)

    if archive_path.stat().st_size != EXPECTED_ZIP_SIZE:
        fail("archive size mismatch")

    if sha256_file(str(archive_path)) != EXPECTED_ZIP_SHA256:
        fail("archive SHA-256 mismatch")

    with zipfile.ZipFile(str(archive_path), "r") as zf:
        if zf.comment:
            fail("archive comment is not empty")

        infos = zf.infolist()
        for info in infos:
            if not safe_member(info.filename):
                fail("unsafe archive path: %s" % info.filename)

        files = [i for i in infos if not i.is_dir()]
        names = [i.filename.replace("\\", "/") for i in files]
        if sorted(names) != sorted(EXPECTED_FILES):
            fail("archive payload file list mismatch: %r" % names)
        if len(names) != len(set(names)):
            fail("duplicate archive payload path")

        for info in files:
            name = info.filename.replace("\\", "/")
            spec = EXPECTED_FILES[name]
            data = zf.read(info)
            if len(data) != spec["size"]:
                fail("size mismatch for %s" % name)
            digest = sha256_bytes(data)
            if digest != spec["sha256"]:
                fail("SHA-256 mismatch for %s" % name)

            repo_path = repo_root / spec["repo"]
            if not repo_path.is_file():
                fail("tracked release file missing: %s" % spec["repo"])
            if sha256_file(str(repo_path)) != spec["sha256"]:
                fail("tracked release file differs from v1.0.1: %s" % spec["repo"])

    print("PASS: v1.0.1 archive identity verified")
    print("PASS: archive paths and exact payload list verified")
    print("PASS: payload sizes and SHA-256 values verified")
    print("PASS: tracked stable payload matches the archive")
    print("ZIP_SHA256=%s" % EXPECTED_ZIP_SHA256)
    return 0


if __name__ == "__main__":
    sys.exit(main())
