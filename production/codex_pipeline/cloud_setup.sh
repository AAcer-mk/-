#!/usr/bin/env bash
set -euo pipefail
cd /workspace/-
for tool in git python3 blender ffmpeg ffprobe node; do command -v "$tool" >/dev/null; done
python3 -m venv /workspace/codex-runtime/venv
/workspace/codex-runtime/venv/bin/python -m pip install -r production/codex_pipeline/requirements.txt
/workspace/codex-runtime/venv/bin/python -m pip check
/workspace/codex-runtime/venv/bin/python production/codex_pipeline/test_recovery_guards.py
# Verify all members, including partial recoveries; do not trust one sentinel.
if ! python3 production/codex_pipeline/verify_recovered_source.py --source /workspace/silent-protocol-source --scope baseline; then
  python3 production/codex_pipeline/ensure_recovery_objects.py --repo /workspace/- --scope all
  python3 production/codex_pipeline/recover_git.py --repo /workspace/- \
    --source /workspace/silent-protocol-source --receipts production/codex_pipeline/qa/recovery
fi
if ! python3 production/codex_pipeline/verify_recovered_source.py --source /workspace/silent-protocol-source --scope rounds; then
  python3 production/codex_pipeline/ensure_recovery_objects.py --repo /workspace/- --scope rounds
  python3 production/codex_pipeline/recover_git.py --repo /workspace/- --rounds-only \
    --source /workspace/silent-protocol-source --receipts production/codex_pipeline/qa/recovery
fi
if ! python3 production/codex_pipeline/verify_recovered_source.py --source /workspace/silent-protocol-source --scope old; then
  python3 production/codex_pipeline/ensure_recovery_objects.py --repo /workspace/- --scope old
  python3 production/sol61/project/restore_payload.py artwork_manifest.json renders_manifest.json
fi
python3 production/codex_pipeline/verify_recovered_source.py --source /workspace/silent-protocol-source
python3 -m venv /workspace/codex-runtime/voice-venv
/workspace/codex-runtime/voice-venv/bin/python -m pip install -r production/codex_pipeline/requirements-voice.lock.txt
/workspace/codex-runtime/voice-venv/bin/python -m pip check
/workspace/codex-runtime/venv/bin/python production/codex_pipeline/setup_voice_models.py --output /workspace/codex-runtime/voice-models
node -e "require('playwright')"
test -x /usr/bin/chromium
/workspace/codex-runtime/venv/bin/python production/codex_pipeline/pipeline.py --source /workspace/silent-protocol-source status
# No render is launched by setup. The agent inspects state and continues work.
