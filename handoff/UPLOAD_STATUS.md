# 文件移交状态（2026-10-09）

## 已直接上传到 GitHub

- `README.md`：项目信息与接管入口
- `docs/ORIGINAL_CREATIVE_BRIEF.txt`：原始完整创作稿（十三部分）
- `docs/BUILD_AND_RESUME.md`、`docs/PRODUCTION_STATUS.md`：工程构建和历史状态
- `handoff/CLAUDE_HANDOFF_INSTRUCTIONS.md`：详细 Claude 接管指令
- `handoff/PROGRESS_AND_CLAUDE_HANDOFF.md`：最新状态
- `handoff/B10_ROUND_RECOVERY_INDEX_VERIFIED.md`：B10 恢复索引与哈希
- `handoff/START_HERE_ORIGINAL.md`、`handoff/B05_BACKUP_DOWNLOADS.md`、`handoff/B05_EXECUTION.md`：历史交接证据
- `audit/FILE_INVENTORY.csv`：905 项归档文件审计数据

**下面的素材目前仍未上传到 GitHub。任何人都不得把当前仓库误报为 905 个工程文件已全部在线。**

## 仍需上传的内容

### 优先（先交给 Claude 继续 E6）

- `SILENT_PROTOCOL_LIGHT_HANDOFF_20261009.zip` — 文本工程、脚本、状态、图像预览与 F6 工作版
- `01_CHARACTER_REFERENCES_ORIGINAL.zip` — 人物原图
- `02_LOCATION_REFERENCES_ORIGINAL.zip` — 场景原图
- `SILENT_PROTOCOL_B10_E6_SUPPLEMENT.zip` — E6 最新候选与检查点
- `14_NATIVE_GRAPHICS_FULLRES.zip` — 图形元素和终端界面

### 后续剪辑需要

- `03_SELECTED_HIRES_SHOTS_01.zip`、`03_SELECTED_HIRES_SHOTS_02.zip`
- `04_RENDER_FONT_ORIGINAL.zip`（遵守字体许可证）
- `05_SCENES_C_E1_E2.zip` 至 `11_E5_BILINGUAL_WORKPRINT.zip` 之间的各场景包
- `12_B10_MASTER_MIX.flac.part01` ～ `part03`（拼接再校验）
- `15_AUDIO_DERIVED_STEMS.zip`、`16_F5_BILINGUAL_WORKPRINT.zip`
- `13_OPTIONAL_ARTBOOK_AND_POSTER.zip`

### 完整无损工程（建议 Git LFS）

- `SILENT_PROTOCOL_PRODUCTION_B05.zip.part01` ～ `part06`（B05 合计 598123268 字节）
- `SILENT_PROTOCOL_B10_P02_DELTA_FROM_B05.zip.part01` ～ `part21`（B10 合计 513581762 字节）
- `SILENT_PROTOCOL_B10_E6_SUPPLEMENT.zip`（15098288 字节）

B05 SHA-256 `5caed769422c04362976c147c39fd0b5c10fcf7d68937f9bc31a7415b6193165`

B10 SHA-256 `8e518dbce60c76f22379af3285e20df882f70ea1a0ae2a4d8de867cc758a0d58`

E6 SHA-256 `3153385b28da2498482dffed1a799b75d5883621912218427ea60c06b1c4ac92`

## Claude 使用方式

Claude 应当先阅读已经在仓库的原始创作稿和交接文档。**没有收到真正的媒体素材之前，不要开始依赖缺失文件的最终合成。**

私有仓库需要 Claude 的 GitHub 连接被授权访问该仓库。拥有 URL 不等于自动拥有权限。

未来素材写入后，更新本文件标记实际已提交内容，并提供对应 commit SHA 与哈希核对证据。


## 2026-10-09 迁移阻塞修复续记

- `scripts/restore_archives.py` 已加固：限制 ZIP 成员数和单包解压大小；拒绝路径穿越、绝对/Windows 路径、符号链接和特殊文件；先检查 CRC 与成员清单，再写入隔离暂存目录，完整成功后才原子发布输出。
- 本地完整真实归档恢复测试通过：905 个文件，1,127,466,957 字节；B05→B10_P02→E6 顺序正确。额外恶意 ZIP 测试拒绝了路径穿越、绝对路径、符号链接和超量成员。
- 小型二进制往返测试通过：`graphics/native_candidates/END-03_v1.png`，6,108 字节，SHA-256 `51e457f4207c6361d8d22571976947233d81f61b45221f4e79f79d25d0d56cf1`。通过 GitHub App 写入迁移分支，再从远端读取 base64 并写入全新临时文件，大小和 SHA-256 一致。详见 `audit/binary_transfer_test.json`。
- 上述图片以普通 Git blob 上传，用于证明小文件二进制通道；它不是 Git LFS 对象或 Release 附件。B05/B10/E6 及其他大型素材仍未上传。LFS 额度与 Release 附件写入能力尚未通过当前执行环境核实。
- 当前终端没有可用 GitHub CLI，Git HTTPS 无凭据；浏览器在安全凭据提交后限制了自动化观察。不得把这些限制绕过成明文令牌或付费额度。
- 继续上传前，需要在自己的终端使用已授权 GitHub 客户端登录，核实 LFS 使用额度/预算；如果 LFS 无合适额度，优先用私有仓库 Release 附件（每个附件小于 2 GiB）保存归档，并保持仓库私有。Release 与 LFS 最终仍须在独立环境下载并校验 SHA-256。
