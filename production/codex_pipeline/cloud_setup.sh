#!/usr/bin/env bash
set -euo pipefail
cd /workspace/-
for tool in git python3 blender ffmpeg ffprobe node; do command -v "$tool" >/dev/null; done
python3 -m venv /workspace/codex-runtime/venv
/workspace/codex-runtime/venv/bin/python -m pip install -r production/codex_pipeline/requirements.txt
/workspace/codex-runtime/venv/bin/python -m pip check
/workspace/codex-runtime/venv/bin/python production/codex_pipeline/test_recovery_guards.py
# Preserve local source and object caches. Fetch large archives only if absent.
if [ ! -f /workspace/silent-protocol-source/project/full_picture_timeline.json ]; then
  git -c fetch.negotiationAlgorithm=noop fetch --refetch --no-filter origin \
    7fbcaebba95371d6f7cb16bb75a7b8f6e29c1edb \
    caa6662db7b695c4ca91740a2840ae603bf0f5f5 \
    887232f3456c8ce132ca98d688e6413863b0575d \
    ddceabc7c15f550a2705ca38068006bdf41dad87 \
    c15958ff2701f9d41ac83044dd595eaf64ccae30
  python3 production/codex_pipeline/recover_git.py --repo /workspace/- \
    --source /workspace/silent-protocol-source --receipts production/codex_pipeline/qa/recovery
  python3 production/sol61/project/restore_payload.py artwork_manifest.json renders_manifest.json
fi
python3 -m venv /workspace/codex-runtime/voice-venv
/workspace/codex-runtime/voice-venv/bin/python -m pip install -r production/codex_pipeline/requirements-voice.lock.txt
/workspace/codex-runtime/voice-venv/bin/python -m pip check
/workspace/codex-runtime/venv/bin/python production/codex_pipeline/setup_voice_models.py --output /workspace/codex-runtime/voice-models
node -e "require('playwright')"
test -x /usr/bin/chromium
/workspace/codex-runtime/venv/bin/python production/codex_pipeline/pipeline.py --source /workspace/silent-protocol-source status
# No render is launched by setup. The agent inspects state and continues work.
