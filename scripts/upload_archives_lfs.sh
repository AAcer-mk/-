#!/usr/bin/env bash
# Upload preserved SILENT PROTOCOL transfer files to an existing clone.
# Usage: bash scripts/upload_archives_lfs.sh /path/to/cloned/repo /path/to/transfer
# transfer should contain parts/ (27 .partXX files) and source/SILENT_PROTOCOL_B10_E6_SUPPLEMENT.zip
set -euo pipefail
ROOT="${1:?Usage: $0 REPO_DIR TRANSFER_DIR}"
TRANSFER="${2:?Usage: $0 REPO_DIR TRANSFER_DIR}"
cd "$ROOT"
command -v git >/dev/null || { echo 'git required'; exit 1; }
git lfs version >/dev/null || { echo 'Git LFS required: https://git-lfs.com/'; exit 1; }
if [[ "$(git rev-parse --show-toplevel)" != "$(pwd -P)" ]]; then
  echo 'Pass the repository root directory'; exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'Refusing to upload: working tree has uncommitted changes'; exit 1
fi
git lfs install --local
git lfs track 'archives/*.part[0-9][0-9]' 'archives/*.zip'
mkdir -p archives
for prefix in SILENT_PROTOCOL_PRODUCTION_B05 SILENT_PROTOCOL_B10_P02_DELTA_FROM_B05; do
  case "$prefix" in
    SILENT_PROTOCOL_PRODUCTION_B05) max=6 ;;
    SILENT_PROTOCOL_B10_P02_DELTA_FROM_B05) max=21 ;;
  esac
  for i in $(seq -w 1 "$max"); do
    file="$TRANSFER/parts/$prefix.zip.part$i"
    [[ -s "$file" ]] || { echo "MISSING: $file"; exit 1; }
    cp -n "$file" archives/
  done
done
supp="$TRANSFER/source/SILENT_PROTOCOL_B10_E6_SUPPLEMENT.zip"
[[ -s "$supp" ]] || { echo "MISSING: $supp"; exit 1; }
cp -n "$supp" archives/
python3 - <<'PY'
import hashlib,pathlib
targets={
'SILENT_PROTOCOL_PRODUCTION_B05':('5caed769422c04362976c147c39fd0b5c10fcf7d68937f9bc31a7415b6193165',6),
'SILENT_PROTOCOL_B10_P02_DELTA_FROM_B05':('8e518dbce60c76f22379af3285e20df882f70ea1a0ae2a4d8de867cc758a0d58',21),
}
for name,(expected,n) in targets.items():
 h=hashlib.sha256()
 for i in range(1,n+1):
  path=pathlib.Path('archives')/f'{name}.zip.part{i:02d}'
  with path.open('rb') as f:
   for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
 actual=h.hexdigest()
 print(name,actual)
 if actual!=expected:raise SystemExit('SHA256 mismatch: '+name)
p=pathlib.Path('archives/SILENT_PROTOCOL_B10_E6_SUPPLEMENT.zip')
actual=hashlib.sha256(p.read_bytes()).hexdigest()
assert actual=='3153385b28da2498482dffed1a799b75d5883621912218427ea60c06b1c4ac92'
print('All archive SHA256 checks passed')
PY
git add .gitattributes archives/
git commit -m "assets: archive verified B05 and B10 project via Git LFS"
git push origin HEAD
echo "Upload complete. Check git lfs ls-files and the remote repository."
