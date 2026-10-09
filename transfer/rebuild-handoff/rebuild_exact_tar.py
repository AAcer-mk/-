#!/usr/bin/env python3
"""Rebuild the exact SILENT_PROTOCOL tar byte stream from recovered files.

This writer uses the original 512-byte member headers recorded in the adjacent
structure JSON. It validates every source payload before writing and never
modifies inputs. The output path must not already exist.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys

BLOCK = 512


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        while True:
            chunk = source.read(4 * 1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def safe_member_path(value: str) -> Path:
    rel = PurePosixPath(value)
    if rel.is_absolute() or not rel.parts or any(part in ("", ".", "..") for part in rel.parts):
        raise ValueError(f"unsafe archive path: {value!r}")
    return Path(*rel.parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--structure", type=Path, default=Path(__file__).with_name("TAR_STRUCTURE.json"))
    parser.add_argument("--source-dir", type=Path, required=True, help="root containing the 905 recovered files")
    parser.add_argument("--output", type=Path, required=True, help="new output path; existing paths are refused")
    args = parser.parse_args()

    structure = json.loads(args.structure.read_text(encoding="utf-8"))
    if structure["format"] != "POSIX_USTAR" or structure["member_count"] != 905:
        raise SystemExit("unsupported structure manifest")
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {args.output}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    written = 0
    try:
        with args.output.open("xb") as target:
            for member in structure["members"]:
                rel = safe_member_path(member["path"])
                source_path = args.source_dir / rel
                if not source_path.is_file():
                    raise SystemExit(f"missing source file: {member['path']}")
                header = base64.b64decode(member["header_block_b64"], validate=True)
                if len(header) != BLOCK:
                    raise SystemExit(f"invalid saved header length for {member['path']}")
                target.write(header)
                digest.update(header)
                written += len(header)

                payload_hash = hashlib.sha256()
                remaining = member["size"]
                with source_path.open("rb") as source:
                    while remaining:
                        chunk = source.read(min(4 * 1024 * 1024, remaining))
                        if not chunk:
                            raise SystemExit(f"short source file: {member['path']}")
                        target.write(chunk)
                        digest.update(chunk)
                        payload_hash.update(chunk)
                        remaining -= len(chunk)
                        written += len(chunk)
                    if source.read(1):
                        raise SystemExit(f"source file is longer than manifest: {member['path']}")
                if payload_hash.hexdigest() != member["payload_sha256"]:
                    raise SystemExit(f"payload SHA-256 mismatch: {member['path']}")

                pad_len = member["data_padding_bytes"]
                padding = base64.b64decode(member["data_padding_b64"], validate=True)
                if len(padding) != pad_len:
                    raise SystemExit(f"invalid saved data padding for {member['path']}")
                target.write(padding)
                digest.update(padding)
                written += len(padding)

            trailer = base64.b64decode(structure["trailing_bytes_b64"], validate=True)
            target.write(trailer)
            digest.update(trailer)
            written += len(trailer)
            target.flush()
            os.fsync(target.fileno())
    except BaseException:
        # The output is always a new, caller-chosen temporary/result path.
        # Keep a partial file for diagnosis; never remove or replace user data.
        raise

    actual_hash = digest.hexdigest()
    if written != structure["archive_bytes"] or actual_hash != structure["archive_sha256"]:
        raise SystemExit(
            f"verification failed: bytes={written} sha256={actual_hash}; "
            f"expected bytes={structure['archive_bytes']} sha256={structure['archive_sha256']}"
        )
    print(json.dumps({"status": "VERIFIED", "bytes": written, "sha256": actual_hash}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
