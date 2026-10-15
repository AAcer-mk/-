#!/usr/bin/env python3
"""Recover immutable migration blobs through existing Git auth, never a raw token.

Each slice, the concatenation, every TAR member, and later round payloads are
checked independently. Existing files are reused only after hashing.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile

BASE = '7fbcaebba95371d6f7cb16bb75a7b8f6e29c1edb'
RANGES = [(1283, 'caa6662db7b695c4ca91740a2840ae603bf0f5f5'),
          (2076, '887232f3456c8ce132ca98d688e6413863b0575d'),
          (2870, 'ddceabc7c15f550a2705ca38068006bdf41dad87')]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def safe_write(root, name, data, expected):
    rel = PurePosixPath(name)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Unsafe path: ' + name)
    dst = root / name
    if not dst.resolve().is_relative_to(root.resolve()):
        raise ValueError('Escaping symlink: ' + name)
    if sha(data) != expected:
        raise ValueError('SHA mismatch: ' + name)
    if dst.exists():
        if sha(dst.read_bytes()) != expected:
            raise ValueError('Refusing to overwrite different existing data: ' + str(dst))
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + '.pending-' + str(os.getpid()))
        with tmp.open('xb') as f:
            f.write(data)
        tmp.replace(dst)


def baseline(repo, destination, receipts):
    manifest_data = git(repo, 'show', RANGES[0][1] + ':transfer/manifest.json')
    assert sha(manifest_data) == '005d632e80e970bf9e8a43ebc9b884b0c80e31ac8f1e9ca59116996df0ef96f8'
    manifest = json.loads(manifest_data)
    parts = manifest['parts']
    assert len(parts) == manifest['part_count'] == 2870
    assert [p['index'] for p in parts] == list(range(1, 2871))
    trees = {ref: dict(line.split('\t', 1)[::-1] for line in
             git(repo, 'ls-tree', '-r', ref).decode().splitlines()) for _, ref in RANGES}
    digest = hashlib.sha256()
    size = 0
    # Only one transient TAR; no duplicate slice checkout or archive rebuild.
    with tempfile.TemporaryFile(dir=destination.parent) as archive:
        cat = subprocess.Popen(['git', '-C', str(repo), 'cat-file', '--batch'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            for number, part in enumerate(parts, 1):
                ref = next(ref for end, ref in RANGES if number <= end)
                entry = trees[ref].get(part['path'])
                if not entry:
                    raise ValueError('Missing part in immutable tree: ' + part['path'])
                oid = entry.split()[2]
                cat.stdin.write((oid + '\n').encode()); cat.stdin.flush()
                header = cat.stdout.readline().decode().split()
                assert len(header) == 3 and header[1] == 'blob', header
                data = cat.stdout.read(int(header[2])); assert cat.stdout.read(1) == b'\n'
                assert len(data) == part['bytes'] and sha(data) == part['sha256'], part['path']
                archive.write(data); digest.update(data); size += len(data)
                if number % 250 == 0:
                    print('Verified migration slices:', number, '/2870', flush=True)
        finally:
            cat.stdin.close(); cat.wait()
        assert size == manifest['archive_bytes'] == 1128171520
        assert digest.hexdigest() == manifest['archive_sha256']
        structure_data = git(repo, 'show', 'c15958ff2701f9d41ac83044dd595eaf64ccae30:transfer/rebuild-handoff/TAR_STRUCTURE.json')
        assert sha(structure_data) == '580e40819af73d1d3c7c02429b6344c7a680ff33c7a3d35cb4d12af03f6caccd'
        structure = json.loads(structure_data)
        wanted = {r['path']: r for r in structure['members']}
        archive.seek(0)
        receipt = []
        with tarfile.open(fileobj=archive, mode='r:') as tf:
            assert len(tf.getmembers()) == len(wanted) == 905
            assert set(tf.getnames()) == set(wanted)
            for member in tf:
                assert member.isfile(), member.name
                data = tf.extractfile(member).read(); row = wanted[member.name]
                assert len(data) == row['size']
                safe_write(destination, member.name, data, row['payload_sha256'])
                receipt.append({'path': member.name, 'bytes': len(data), 'sha256': sha(data)})
    report = {'parts_verified': 2870, 'archive_bytes': size,
              'archive_sha256': digest.hexdigest(), 'members_verified': len(receipt),
              'source_refs': RANGES, 'files': receipt}
    (receipts / 'baseline_recovery.json').write_text(json.dumps(report, indent=2))
    print('Baseline verified:', len(receipt), 'members', flush=True)


def round_payload(repo, number, receipts):
    folder = f'production/sol61_r{number}'
    manifest = json.loads(git(repo, 'show', BASE + ':' + folder + '/PAYLOAD_MANIFEST.json'))
    with tempfile.TemporaryFile(dir=receipts.parent) as archive:
        digest = hashlib.sha256(); size = 0
        for part in manifest['parts']:
            data = git(repo, 'show', BASE + ':' + folder + '/' + part['path'])
            assert len(data) == part['bytes'] and sha(data) == part['sha256']
            digest.update(data); size += len(data); archive.write(data)
        assert size == manifest['bytes'] and digest.hexdigest() == manifest['sha256']
        archive.seek(0); wanted = {r['path']: r for r in manifest['members']}
        with tarfile.open(fileobj=archive) as tf:
            assert len(tf.getmembers()) == len(wanted) and set(tf.getnames()) == set(wanted)
            for member in tf:
                assert member.isfile()
                data = tf.extractfile(member).read(); row = wanted[member.name]
                assert len(data) == row['bytes']
                safe_write(repo / folder, member.name, data, row['sha256'])
    (receipts / f'r{number}_recovery.json').write_text(json.dumps({
        'commit': BASE, 'parts_verified': len(manifest['parts']), 'members_verified': len(wanted),
        'archive_sha256': digest.hexdigest(), 'destination': folder}, indent=2))
    print('Round', number, 'verified:', len(wanted), 'members', flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--receipts', type=Path, required=True)
    p.add_argument('--rounds-only', action='store_true')
    args = p.parse_args(); args.receipts.mkdir(parents=True, exist_ok=True)
    if not args.rounds_only:
        baseline(args.repo, args.source, args.receipts)
    for n in range(2, 7):
        round_payload(args.repo, n, args.receipts)


if __name__ == '__main__':
    main()
