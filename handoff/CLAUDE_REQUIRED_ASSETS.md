# Claude 续作所需素材清单（2026-10-09，依据仓库现有文档整理）

本清单只列**确定需要**的文件，来源均为 `handoff/`、`docs/`、`README.md` 中已写明的名称与哈希。尚未在仓库中出现的文件以「未上传」标注。续作者：Claude；生成类任务由 Sol 执行（见第 4 节）。

## 1. 第一优先：能否核验与恢复工程（缺一不可）

| 文件 | 大小/哈希 | 用途 | 仓库现状 |
|---|---|---|---|
| `SILENT_PROTOCOL_PRODUCTION_B05.zip.part01`–`part06` | 合计 598,123,268 B；SHA-256 `5caed769…6193165` | 完整基线工程 | 未上传 |
| `SILENT_PROTOCOL_B10_P02_DELTA_FROM_B05.zip.part01`–`part21` | 合计 513,581,762 B；SHA-256 `8e518dbc…0a58` | B05 之上的增量（含 F6 工作成果） | 未上传 |
| `SILENT_PROTOCOL_B10_E6_SUPPLEMENT.zip` | 15,098,288 B；SHA-256 `3153385b…ac92` | E6 最新候选与 checkpoint | 未上传 |
| `TRANSFER_INDEX.json` | — | 分卷/包的逐文件哈希与大小（交接说明 §7 引用） | 未上传 |
| 各分卷的逐卷 SHA-256 | B05 六卷哈希见 `handoff/B05_BACKUP_DOWNLOADS.md`；B10 的 21 卷哈希在 `B10_P02_VOLUMES.json` | 逐卷核验，定位损坏卷 | B05 已有；B10 未上传 |

这三组恢复后应得到 905 个文件（约 1.127 GB），与 `audit/FILE_INVENTORY.csv` 逐项对照。**这一组到齐，其余第 2 节大部分文件会重复包含其中，可不再单独上传。**

恢复顺序固定：B05 → B10_P02 → E6 补充，解到全新目录，原包只读。仓库已有的 `scripts/restore_archives.py` 按此顺序执行。

## 2. 备选：若完整分卷暂时传不了，先给这些（轻量接管包）

均出自 `handoff/CLAUDE_HANDOFF_INSTRUCTIONS.md`，每个 <30 MiB：

- `SILENT_PROTOCOL_LIGHT_HANDOFF_20261009.zip`：文本工程、脚本、checkpoint、素材状态表、172 张低分辨率预览、有损试听混音、F6 双语工作片。**仅预览质量，不能当高清源。**
- `01_CHARACTER_REFERENCES_ORIGINAL.zip`（13 张人物原 PNG）、`02_LOCATION_REFERENCES_ORIGINAL.zip`（10 张场景原 PNG）：Sol 生成新镜头时的一致性参考，**必须原图**。
- `SILENT_PROTOCOL_B10_E6_SUPPLEMENT.zip`：同上。
- `14_NATIVE_GRAPHICS_FULLRES.zip`：原尺寸界面/终端/字卡图形。

进入剪辑与成片阶段还需要（若不走第 1 节整包）：`03_SELECTED_HIRES_SHOTS_01/02.zip`、`04_RENDER_FONT_ORIGINAL.zip`（先确认字体许可证）、`05`–`11`、`16` 各场景工作版、`12_B10_MASTER_MIX.flac.part01`–`part03`（按序字节拼接，对 `TRANSFER_INDEX.json` 核哈希）、`15_AUDIO_DERIVED_STEMS.zip`。

## 3. 恢复后我会立刻读取的状态文件（在上述包内，仓库目前没有）

`READ_FIRST.md`、`HANDOFF/RECOVERY_INDEX_VERIFIED.md`、`state/checkpoint.json`、`CHECKPOINT_B10_FINAL.json`、`project/selected_candidates.json`、`project/assets_manifest.json`、`project/RESUME_IMAGE_QUEUE.json`、`project/*.py`（`build_timeline.py`、`film_compositor.py`、`assemble_film.py`、`final_audio.py`、`checkpoint.py`、`resume_control.py`）、`project/requirements-render.txt`、`project/runtime_versions.json`、全部字幕 SRT/ASS。

## 4. 需要 Sol 执行的生成任务（Claude 负责出任务单、接收与合成）

Claude 的环境无图像/视频生成能力。镜头任务单将在核对 checkpoint 后逐镜输出，范围：E6-04 第 3 张；E6-05、E6-07 各 3 张；F7→E7→F8→E8→F9→E9→END 中无候选的镜头（记录显示约 37 镜）。每镜任务包含：原稿分镜原文、时长、画幅、人物/场景参考文件名、色彩脚本（饱和度）、连续性要求、屏幕文字说明、验收标准。

Sol 交回时请遵守：
1. 文件放入独立工作分支，命名与原工程候选一致（以 B05 内 `art/` 现有命名为准），每镜 ≥3 个候选；
2. 附生成记录：提示词、所用参考图、模型/工具、时间、分辨率；
3. **画面内的屏幕文字、聊天、日志、面单、倒计时一律不要生成**，留空，由 Claude 用真实字体后期合成；
4. 不得出现真实公司 Logo、真实人物；九个模型只用原稿的原创符号；
5. 失败或被拒的生成也要记录，不要静默跳过；
6. 已完成的 F6 及其他已验收镜头不要重做。

## 5. 保留、不得使用的证据文件

`evidence/E3-08_v1_DERIVATIVE_TRUNCATED.png`、`E6-02_v2_DERIVATIVE_TRUNCATED.png`、`E9-07_v1_DERIVATIVE_TRUNCATED.png`、`E9-07_v2_TRUNCATED_original.png`；`evidence/B05_failed_ipod_mux_FLAC.m4a`、`output/sections/F5_picture_clean_v4_1080p.mp4`、`qa/END03_ALAC_CODEC_REHEARSAL_NOT_FILM.mp4`。仅作证据保留，不进入剪辑。

## 6. 上传前请 Luna 确认

- LFS 容量与流量够用（费用由 Luna/用户处理，Claude 不购买额度、不改仓库付费设置）；
- 任何单文件 >100 MB 必须走 LFS 或分卷；
- 上传完成后更新 `handoff/UPLOAD_STATUS.md`，注明 commit SHA 与哈希核对结果。
