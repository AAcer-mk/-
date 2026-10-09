#!/usr/bin/env python3
"""Restore SILENT PROTOCOL from verified B05 + B10 + E6 archive volumes.

Run after downloading Git LFS files:
    git lfs pull
    python3 scripts/restore_archives.py --output ./restored-film

No source archive is modified. The output path must not already exist.
"""
import argparse
import hashlib
import pathlib
import tempfile
import zipfile

SPEC = [
    ("SILENT_PROTOCOL_PRODUCTION_B05", 6,
     "5caed769422c04362976c147c39fd0b5c10fcf7d68937f9bc31a7415b6193165"),
    ("SILENT_PROTOCOL_B10_P02_DELTA_FROM_B05", 21,
     "8e518dbce60c76f22379af3285e20df882f70ea1a0ae2a4d8de867cc758a0d58")
]
E6 = "3153385b28da2498482dffed1a799b75d5883621912218427ea60c06b1c4ac92"

def checksum(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()

def reassemble(folder, spec, scratch):
    name, count, expected = spec
    out = scratch / (name + '.zip')
    with out.open('wb') as dst:
        for num in range(1, count + 1):
            part = folder / f'{name}.zip.part{num:02d}'
            if not part.is_file():
                raise FileNotFoundError(str(part))
            with part.open('rb') as src:
                for data in iter(lambda: src.read(4 * 1024 * 1024), b''):
                    dst.write(data)
    if checksum(out) != expected:
        raise ValueError('SHA256 mismatch: ' + str(out))
    return out

def safe_overlay(archive, output):
    with zipfile.ZipFile(archive) as zf:
        error = zf.testzip()
        if error:
            raise ValueError(f'CRC failed in {archive.name}: {error}')
        resolved = output.resolve()
        for item in zf.infolist():
            rel = pathlib.PurePosixPath(item.filename)
            if rel.is_absolute() or '..' in rel.parts:
                raise ValueError(f'Unsafe archive member: {item.filename}')
            target = (output / item.filename).resolve()
            if not target.is_relative_to(resolved):
                raise ValueError('Path traversal blocked')
        zf.extractall(output)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--archives', type=pathlib.Path, default=pathlib.Path('archives'))
    p.add_argument('--output', type=pathlib.Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error('Output directory already exists; choose an unused directory')
    supp = args.archives / 'SILENT_PROTOCOL_B10_E6_SUPPLEMENT.zip'
    if not supp.is_file() or checksum(supp) != E6:
        p.error('E6 supplement missing or hash mismatch')
    # Validate everything before creating the output folder.
    with tempfile.TemporaryDirectory(prefix='silent-protocol-archives-') as scratch:
        archives = [reassemble(args.archives, spec, pathlib.Path(scratch)) for spec in SPEC]
        for archive in archives + [supp]:
            with zipfile.ZipFile(archive) as zf:
                if zf.testzip():
                    raise ValueError('Archive CRC failed: ' + str(archive))
        args.output.mkdir(parents=True, exist_ok=False)
        for archive in archives + [supp]:
            safe_overlay(archive, args.output)
        print('Restored to', args.output.resolve())
        print('Files:', sum(p.is_file() for p in args.output.rglob('*')))
        print('This is a recovered work-in-progress, NOT a final movie.')

if __name__ == '__main__':
    main()
