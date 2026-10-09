#!/usr/bin/env bash
# Usage: bash scripts/upload_priority_assets.sh /path/to/cloned/repo /path/to/downloads
# Downloads should contain SILENT_PROTOCOL_LIGHT_HANDOFF_20261009.zip
# and SILENT_PROTOCOL_CLAUDE_ASSETS_20261009/ with named asset archives.
set -euo pipefail
repo="${1:?Pass local repository path}"
downloads="${2:?Pass folder containing downloaded handoff ZIP files}"
cd "$repo"
git lfs version >/dev/null || { echo "Install Git LFS first: https://git-lfs.com"; exit 1; }
[[ -z "$(git status --porcelain)" ]] || { echo "Working tree not clean"; exit 1; }
git lfs install --local
git lfs track 'media/priority/*.zip' 'media/priority/*.part[0-9][0-9]'
mkdir -p media/priority
find "$downloads" -maxdepth 3 -type f \( -name '*.zip' -o -name '12_B10_MASTER_MIX.flac.part*' \) -print0 | while IFS= read -r -d '' file; do
   case "$(basename "$file")" in
     SILENT_PROTOCOL_CLAUDE_FULL_TRANSFER_20261009.zip|SILENT_PROTOCOL_PRODUCTION_B05*|SILENT_PROTOCOL_B10_P02*) continue ;;
   esac
   cp -n "$file" "media/priority/$(basename "$file")"
done
[[ -f media/priority/SILENT_PROTOCOL_LIGHT_HANDOFF_20261009.zip ]] || {
  echo "No light handoff ZIP was found; check downloads path"; exit 1;
}
git add .gitattributes media/priority
git commit -m 'assets: add light handoff and prioritized production media using Git LFS'
git push origin HEAD
git lfs ls-files
echo 'Priority upload complete; update handoff/UPLOAD_STATUS.md after verifying remote files.'
