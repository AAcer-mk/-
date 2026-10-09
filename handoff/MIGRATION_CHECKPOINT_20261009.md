# Migration checkpoint — 2026-10-09

## State

This branch records the verified source recovery performed for the GitHub migration. It is a checkpoint only. **The binary project archives and restored project are not yet present in this repository**, and the migration must not be described as complete.

Repository: `AAcer-mk/-`  
Base at start of this checkpoint: `df34c2dd2a77cc32c92f868b06b6c8dc37753810`  
The repository remains private. The connected GitHub account reports push permission.

## Verified source set

The canonical source files were resolved from the user's Library and copied into an isolated source directory. All original source parts were retained.

| Package | Parts | Reassembled size | SHA-256 |
|---|---:|---:|---|
| `SILENT_PROTOCOL_PRODUCTION_B05.zip` | 6 | 598,123,268 bytes | `5caed769422c04362976c147c39fd0b5c10fcf7d68937f9bc31a7415b6193165` |
| `SILENT_PROTOCOL_B10_P02_DELTA_FROM_B05.zip` | 21 | 513,581,762 bytes | `8e518dbce60c76f22379af3285e20df882f70ea1a0ae2a4d8de867cc758a0d58` |
| `SILENT_PROTOCOL_B10_E6_SUPPLEMENT.zip` | 1 | 15,098,288 bytes | `3153385b28da2498482dffed1a799b75d5883621912218427ea60c06b1c4ac92` |

All three reassembled packages passed SHA-256 and ZIP CRC checks. The B10_P02 manifest's 469 entries and E6 supplement manifest's 25 entries matched their extracted file sizes and SHA-256 values.

## Isolated recovery results

Recovery order was B05 → B10_P02 → E6. The extracted layers contain 920 files (1,128,132,497 bytes); the final overlaid work-in-progress contains 905 files (1,127,466,957 bytes). Eleven path overlays were recorded with prior and replacement hashes; all layers remain preserved. The latest assets manifest reports 152 timeline segments, 140 picture shots, 294 valid candidates, 126 missing candidates, and `creative_final_pass=false`. The checkpoint says the final film is not complete and E6 is in progress.

Full media checks covered 70 audio/video files: 67 passed ffprobe and full decode. Three failures were preserved as evidence: a zero-byte failed mux, F5 v4 with no MP4 `moov` atom, and an ALAC codec rehearsal marked NOT_FILM with no `moov` atom. Project Python sources passed compileall. Exact audit outputs from this local verification were written under `migration-derived/restored/audit/`; they are not included in this GitHub commit.

## Transfer blocker

The shell environment could not clone or push because it has no GitHub HTTPS credential (`could not read Username`). The GitHub app connection can inspect the private repo and confirms push permission, but it exposes no Git LFS object upload flow. Git LFS enablement, quota, and billing status remain unverified. No LFS upload, binary upload, purchase, privacy change, or force push was performed. A clean remote clone and restore test could not be run.

## Resume safely

1. Obtain an authorized Git credential in an environment that can run Git and Git LFS, or use an approved Git LFS transfer workflow.
2. Before uploading, verify LFS is enabled and check storage/bandwidth quota and any cost implications. Do not change paid settings without owner approval.
3. Start from the current `main` without rewriting history, apply the audited assets and a hardened restore script on a migration branch, and push in resumable batches.
4. Download the LFS objects in a fresh clone, run SHA-256/CRC checks, restore B05 → B10_P02 → E6, then verify the result before merging.
5. Keep the repository private and grant Claude explicit read access through its GitHub connection.

This checkpoint does not certify GitHub migration, remote asset availability, Claude access, or final-film completion.
