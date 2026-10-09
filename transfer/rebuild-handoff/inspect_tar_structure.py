#!/usr/bin/env python3
"""Create a byte-level structure inventory for the verified archive."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import tarfile

BLOCK = 512
EXPECTED_SHA256 = "2f07d56ff635894e6792265e25abb3392b7896879e186c271e53407f52fc4e39"


def sha256_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        while chunk := f.read(4 * 1024 * 1024):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def field(block: bytes, start: int, end: int) -> str:
    raw = block[start:end].split(b"\0", 1)[0]
    return raw.decode("utf-8", "backslashreplace")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--source-dir", type=Path, help="optional recovered tree; if supplied, verify all member bytes")
    args = ap.parse_args()

    archive_sha, archive_bytes = sha256_file(args.archive)
    if archive_sha != EXPECTED_SHA256:
        raise SystemExit(f"refusing unexpected archive SHA-256: {archive_sha}")

    members = []
    last_end = 0
    with tarfile.open(args.archive, "r:") as tf, args.archive.open("rb") as raw:
        for m in tf.getmembers():
            if not m.isfile() or m.type not in (tarfile.REGTYPE, tarfile.AREGTYPE):
                raise SystemExit(f"non-regular member found: {m.name!r} type={m.type!r}")
            if m.pax_headers:
                raise SystemExit(f"PAX headers found: {m.name!r}")
            raw.seek(m.offset)
            header = raw.read(BLOCK)
            if len(header) != BLOCK:
                raise SystemExit(f"short header block at {m.offset}")
            if header[257:263] != b"ustar\0" or header[263:265] != b"00":
                raise SystemExit(f"member header is not POSIX USTAR: {m.name!r}")
            size = m.size
            pad_len = (-size) % BLOCK
            raw.seek(m.offset_data + size)
            padding = raw.read(pad_len)
            if len(padding) != pad_len or any(padding):
                raise SystemExit(f"nonzero/short data padding: {m.name!r}")
            checksum_field = header[148:156].strip(b" \0") or b"0"
            stored_checksum = int(checksum_field, 8)
            calculated_checksum = sum(header[:148] + b" " * 8 + header[156:])
            if stored_checksum != calculated_checksum:
                raise SystemExit(f"header checksum mismatch: {m.name!r}")
            payload_hash = hashlib.sha256()
            source = tf.extractfile(m)
            assert source is not None
            while chunk := source.read(4 * 1024 * 1024):
                payload_hash.update(chunk)
            if args.source_dir:
                p = args.source_dir.joinpath(*Path(m.name).parts)
                if not p.is_file() or p.stat().st_size != size:
                    raise SystemExit(f"recovered source missing/size mismatch: {m.name!r}")
                source_hash, source_size = sha256_file(p)
                if source_size != size or source_hash != payload_hash.hexdigest():
                    raise SystemExit(f"recovered source content mismatch: {m.name!r}")
            members.append({
                "path": m.name,
                "typeflag": header[156:157].decode("ascii", "replace"),
                "size": size,
                "mode": m.mode,
                "uid": m.uid,
                "gid": m.gid,
                "mtime": m.mtime,
                "header_offset": m.offset,
                "data_offset": m.offset_data,
                "data_padding_bytes": pad_len,
                "data_padding_b64": base64.b64encode(padding).decode("ascii"),
                "payload_sha256": payload_hash.hexdigest(),
                "header_name_field": field(header, 0, 100),
                "header_mode_octal": field(header, 100, 108),
                "header_uid_octal": field(header, 108, 116),
                "header_gid_octal": field(header, 116, 124),
                "header_size_octal": field(header, 124, 136),
                "header_mtime_octal": field(header, 136, 148),
                "header_checksum_field": field(header, 148, 156),
                "header_linkname_field": field(header, 157, 257),
                "ustar_magic": header[257:263].decode("ascii", "replace"),
                "ustar_version": header[263:265].decode("ascii", "replace"),
                "header_uname_field": field(header, 265, 297),
                "header_gname_field": field(header, 297, 329),
                "ustar_prefix_field": field(header, 345, 500),
                "header_block_b64": base64.b64encode(header).decode("ascii"),
            })
            last_end = m.offset_data + size + pad_len

        raw.seek(last_end)
        trailer = raw.read()
        if len(trailer) != archive_bytes - last_end or len(trailer) % BLOCK or any(trailer):
            raise SystemExit("trailing TAR bytes are not an all-zero block-aligned trailer")

    result = {
        "format": "POSIX_USTAR",
        "archive_name": args.archive.name,
        "archive_bytes": archive_bytes,
        "archive_sha256": archive_sha,
        "block_bytes": BLOCK,
        "record_bytes": 10240,
        "member_count": len(members),
        "members": members,
        "trailing_bytes": len(trailer),
        "trailing_bytes_b64": base64.b64encode(trailer).decode("ascii"),
        "trailing_all_zero": not any(trailer),
        "pax_header_count": 0,
        "directory_entry_count": 0,
        "member_type_counts": {"regular_file": len(members)},
        "uid_values": sorted({m["uid"] for m in members}),
        "gid_values": sorted({m["gid"] for m in members}),
        "mtime_values": sorted({m["mtime"] for m in members}),
        "mode_values_octal": sorted({oct(m["mode"]) for m in members}),
        "creation_procedure": "not found in available workspace logs/scripts; member structure captured byte-for-byte from verified TAR",
    }
    args.output.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "members"}, sort_keys=True))


if __name__ == "__main__":
    main()
