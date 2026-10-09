#!/usr/bin/env python3
"""Verify and restore SILENT_PROTOCOL_COMPLETE_B10.tar from numbered parts.

Run from the repository root after obtaining the transfer directory:
  python3 transfer/restore.py --manifest transfer/manifest.json \
    --inventory audit/verified_assets.csv --output ./SILENT_PROTOCOL_RESTORED

The script never overwrites an existing output. It verifies every part, the
whole TAR SHA-256, safe TAR member types/paths, inventory paths, sizes and file
SHA-256 values before atomically publishing the staged restore.
"""
import argparse
import csv
import hashlib
import json
import os
import pathlib
import shutil
import stat
import tarfile
import tempfile

CHUNK = 4 * 1024 * 1024


def digest_stream(stream, target=None):
    h = hashlib.sha256()
    total = 0
    while True:
        data = stream.read(CHUNK)
        if not data:
            break
        h.update(data)
        total += len(data)
        if target is not None:
            target.write(data)
    return total, h.hexdigest()


def safe_relative(name):
    if not name or "\\" in name or name.startswith("/") or "\x00" in name:
        raise ValueError(f"Unsafe archive path: {name!r}")
    rel = pathlib.PurePosixPath(name)
    if rel.is_absolute() or any(p in ("", ".", "..") for p in rel.parts):
        raise ValueError(f"Unsafe archive path: {name!r}")
    if rel.parts and ":" in rel.parts[0]:
        raise ValueError(f"Drive path rejected: {name!r}")
    return rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=pathlib.Path, default=pathlib.Path("transfer/manifest.json"))
    ap.add_argument("--inventory", type=pathlib.Path, default=pathlib.Path("transfer/source_inventory.csv"))
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    manifest_path = args.manifest.resolve()
    repo_root = manifest_path.parent.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    inventory_path = args.inventory if args.inventory.is_absolute() else repo_root / args.inventory
    out = args.output.absolute()
    if out.exists() or out.is_symlink():
        ap.error("Output must be a new, unused path")
    inventory_rows = list(csv.DictReader(inventory_path.open(encoding="utf-8-sig", newline="")))
    expected = {safe_relative(r["path"]).as_posix(): (int(r["bytes"]), r["sha256"]) for r in inventory_rows}
    if len(expected) != len(inventory_rows) or len(expected) != manifest["source_file_count"]:
        raise ValueError("Inventory count or duplicate paths do not match the manifest")
    parts = manifest["parts"]
    if len(parts) != manifest["part_count"] or [p["index"] for p in parts] != list(range(1, len(parts) + 1)):
        raise ValueError("Missing, duplicate, or out-of-order volume indexes")
    part_paths = [p["path"] for p in parts]
    if len(set(part_paths)) != len(part_paths):
        raise ValueError("Duplicate part paths")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="silent-protocol-restore-") as temp_name:
        temp = pathlib.Path(temp_name)
        tar_path = temp / manifest["archive_name"]
        whole = hashlib.sha256()
        written = 0
        with tar_path.open("xb") as dst:
            for part in parts:
                src_path = repo_root / safe_relative(part["path"])
                if not src_path.is_file() or src_path.is_symlink():
                    raise FileNotFoundError(f"Missing or unsafe volume: {src_path}")
                h = hashlib.sha256()
                count = 0
                with src_path.open("rb") as src:
                    while True:
                        data = src.read(CHUNK)
                        if not data:
                            break
                        h.update(data); whole.update(data); dst.write(data); count += len(data)
                if count != part["bytes"] or h.hexdigest() != part["sha256"]:
                    raise ValueError(f"Part size/SHA-256 mismatch: {src_path}")
                written += count
        if written != manifest["archive_bytes"] or whole.hexdigest() != manifest["archive_sha256"]:
            raise ValueError("Reassembled TAR size/SHA-256 mismatch")
        stage = pathlib.Path(tempfile.mkdtemp(prefix=".silent-protocol-stage-", dir=out.parent))
        try:
            with tarfile.open(tar_path, "r:") as tf:
                members = tf.getmembers()
                if len(members) != len(expected):
                    raise ValueError(f"TAR file count mismatch: {len(members)} != {len(expected)}")
                seen = set()
                declared_total = 0
                for m in members:
                    rel = safe_relative(m.name).as_posix()
                    if rel in seen or rel not in expected:
                        raise ValueError(f"Duplicate or unexpected TAR path: {rel}")
                    seen.add(rel)
                    if not m.isfile() or m.issym() or m.islnk() or m.isdev() or m.isdir():
                        raise ValueError(f"Non-regular TAR member rejected: {rel}")
                    expected_size, _ = expected[rel]
                    if m.size != expected_size:
                        raise ValueError(f"TAR member size mismatch: {rel}")
                    declared_total += m.size
                if seen != set(expected) or declared_total != manifest["source_bytes"]:
                    raise ValueError("TAR paths or total size do not match source inventory")
                for m in members:
                    rel = safe_relative(m.name)
                    target = stage.joinpath(*rel.parts)
                    if not target.resolve(strict=False).is_relative_to(stage.resolve()):
                        raise ValueError(f"Extraction escapes staging directory: {m.name}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    src = tf.extractfile(m)
                    if src is None:
                        raise ValueError(f"Cannot read TAR member: {m.name}")
                    h = hashlib.sha256(); count = 0
                    with src, target.open("xb") as dst:
                        while True:
                            data = src.read(CHUNK)
                            if not data:
                                break
                            h.update(data); dst.write(data); count += len(data)
                    expected_size, expected_sha = expected[rel.as_posix()]
                    if count != expected_size or h.hexdigest() != expected_sha:
                        raise ValueError(f"Restored file hash mismatch: {rel}")
            os.rename(stage, out)
        except BaseException:
            shutil.rmtree(stage, ignore_errors=True)
            raise
    print(f"RESTORE_PASS files={len(expected)} bytes={manifest['source_bytes']} archive_sha256={manifest['archive_sha256']}")
    print(f"output={out}")


if __name__ == "__main__":
    main()
