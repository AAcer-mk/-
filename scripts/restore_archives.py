#!/usr/bin/env python3
"""Safely restore SILENT PROTOCOL in order: B05, B10_P02, then E6.

The source archives are read-only. All ZIPs are fully CRC-tested and preflighted
before extraction. Extraction is staged beside the destination and atomically
renamed into place only after success.
"""
import argparse
import hashlib
import os
import pathlib
import shutil
import stat
import tempfile
import zipfile

SPEC = [
    ("SILENT_PROTOCOL_PRODUCTION_B05", 6, 598123268,
     "5caed769422c04362976c147c39fd0b5c10fcf7d68937f9bc31a7415b6193165"),
    ("SILENT_PROTOCOL_B10_P02_DELTA_FROM_B05", 21, 513581762,
     "8e518dbce60c76f22379af3285e20df882f70ea1a0ae2a4d8de867cc758a0d58"),
]
E6_NAME = "SILENT_PROTOCOL_B10_E6_SUPPLEMENT.zip"
E6_SIZE = 15098288
E6_SHA = "3153385b28da2498482dffed1a799b75d5883621912218427ea60c06b1c4ac92"
CHUNK = 4 * 1024 * 1024


def checksum(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda: f.read(CHUNK), b""):
            h.update(data)
    return h.hexdigest()


def reassemble(folder, spec, scratch):
    name, count, size, expected = spec
    out = scratch / (name + ".zip")
    with out.open("xb") as dst:
        for num in range(1, count + 1):
            part = folder / f"{name}.zip.part{num:02d}"
            if not part.is_file() or part.is_symlink():
                raise FileNotFoundError(f"Missing or unsafe volume: {part}")
            with part.open("rb") as src:
                shutil.copyfileobj(src, dst, CHUNK)
    if out.stat().st_size != size or checksum(out) != expected:
        raise ValueError(f"Size/SHA-256 mismatch: {out}")
    return out


def member_path(info):
    name = info.filename
    if not name or "\\" in name or name.startswith("/") or "\x00" in name:
        raise ValueError(f"Unsafe ZIP path: {name!r}")
    path = pathlib.PurePosixPath(name)
    if any(part in ("", ".", "..") for part in path.parts) or (path.parts and ":" in path.parts[0]):
        raise ValueError(f"Unsafe ZIP path: {name!r}")
    mode = (info.external_attr >> 16) & 0xFFFF
    kind = stat.S_IFMT(mode)
    is_dir = info.is_dir()
    if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise ValueError(f"Unsupported special ZIP member: {name!r}")
    if kind == stat.S_IFDIR and not is_dir:
        raise ValueError(f"Inconsistent ZIP directory entry: {name!r}")
    if is_dir and info.file_size != 0:
        raise ValueError(f"Non-empty ZIP directory entry: {name!r}")
    if info.flag_bits & 0x1:
        raise ValueError(f"Encrypted ZIP member is unsupported: {name!r}")
    return path, is_dir


def preflight(archive, max_bytes, max_files):
    with zipfile.ZipFile(archive) as zf:
        infos = zf.infolist()
        if len(infos) > max_files:
            raise ValueError(f"Too many ZIP entries in {archive.name}: {len(infos)} > {max_files}")
        total = 0
        seen = set()
        for info in infos:
            path, is_dir = member_path(info)
            key = path.as_posix().rstrip("/")
            if key in seen:
                raise ValueError(f"Duplicate ZIP path in {archive.name}: {key}")
            seen.add(key)
            total += info.file_size
            if total > max_bytes:
                raise ValueError(f"Expanded size limit exceeded in {archive.name}")
        bad = zf.testzip()
        if bad:
            raise ValueError(f"ZIP CRC failed in {archive.name}: {bad}")
        return len(infos), total


def overlay(archive, stage):
    with zipfile.ZipFile(archive) as zf:
        root = stage.resolve()
        for info in zf.infolist():
            rel, is_dir = member_path(info)
            target = stage.joinpath(*rel.parts)
            resolved = target.resolve(strict=False)
            if not resolved.is_relative_to(root):
                raise ValueError(f"Path escapes staging directory: {info.filename!r}")
            if is_dir:
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.is_dir():
                raise ValueError(f"File/directory collision: {info.filename!r}")
            # Overlay later layers (B10/E6) over earlier versions in stage only.
            with zf.open(info, "r") as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst, CHUNK)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archives", type=pathlib.Path, default=pathlib.Path("archives"))
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--max-expanded-bytes", type=int, default=10 * 1024**3)
    parser.add_argument("--max-files", type=int, default=20000)
    args = parser.parse_args()
    source = args.archives.resolve()
    output = args.output.absolute()
    if not source.is_dir():
        parser.error(f"Archive directory not found: {source}")
    if output.exists() or output.is_symlink():
        parser.error("Output must be a new, unused path")
    output.parent.mkdir(parents=True, exist_ok=True)
    supp = source / E6_NAME
    if not supp.is_file() or supp.is_symlink() or supp.stat().st_size != E6_SIZE or checksum(supp) != E6_SHA:
        parser.error("E6 supplement missing or size/SHA-256 mismatch")
    with tempfile.TemporaryDirectory(prefix="silent-protocol-archives-") as scratch_name:
        scratch = pathlib.Path(scratch_name)
        archives = [reassemble(source, spec, scratch) for spec in SPEC] + [supp]
        counts = [preflight(z, args.max_expanded_bytes, args.max_files) for z in archives]
        stage_parent = output.parent
        stage = pathlib.Path(tempfile.mkdtemp(prefix=".silent-protocol-stage-", dir=stage_parent))
        try:
            for archive in archives:
                overlay(archive, stage)
            os.rename(stage, output)
        except BaseException:
            shutil.rmtree(stage, ignore_errors=True)
            raise
    files = sum(p.is_file() for p in output.rglob("*"))
    size = sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
    print(f"Restored: {output}")
    print(f"ZIP entries preflighted: {sum(n for n, _ in counts)}; expanded bytes declared: {sum(b for _, b in counts)}")
    print(f"Output files: {files}; bytes: {size}")
    print("Recovered work-in-progress; not a final movie.")

if __name__ == "__main__":
    main()
