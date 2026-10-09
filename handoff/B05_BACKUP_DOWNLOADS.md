# B05 工程分卷下载与重组

这是制作中的完整工作工程备份，不是正式成片。含源素材、分镜、音轨、字幕、代码、10 个已恢复的前段视频、40 秒片尾以及检测证据。中间 630 秒仍未完成。

六个分卷按 01 到 06 顺序拼接，不能单独当 ZIP 解压。前五卷每卷 100 MiB，末卷约 70.4 MiB。下载后保留原文件名。

| 分卷 | 文件 | SHA256 |
|---|---|---|
| 01 | [SILENT_PROTOCOL_PRODUCTION_B05.zip.part01](sandbox:/workspace/scratch/1c83c98bee20/silent_protocol_resume_20261008_2037/checkpoints/SILENT_PROTOCOL_PRODUCTION_B05.zip.part01) | 5b59a52380ee850c24ff2ea222ab0fcfe9ae9da2e2fc2fe34388cb54f4076a73 |
| 02 | [SILENT_PROTOCOL_PRODUCTION_B05.zip.part02](sandbox:/workspace/scratch/1c83c98bee20/silent_protocol_resume_20261008_2037/checkpoints/SILENT_PROTOCOL_PRODUCTION_B05.zip.part02) | b39a043c41734a9e3a7c54ec9a9e6f03ef89f4249d93a029ff66dd19fdbd5185 |
| 03 | [SILENT_PROTOCOL_PRODUCTION_B05.zip.part03](sandbox:/workspace/scratch/1c83c98bee20/silent_protocol_resume_20261008_2037/checkpoints/SILENT_PROTOCOL_PRODUCTION_B05.zip.part03) | 6f417170b4d39b6569d08609635acb7fae161070d8990d092b08de11de41cee8 |
| 04 | [SILENT_PROTOCOL_PRODUCTION_B05.zip.part04](sandbox:/workspace/scratch/1c83c98bee20/silent_protocol_resume_20261008_2037/checkpoints/SILENT_PROTOCOL_PRODUCTION_B05.zip.part04) | cf3c731c2be83ca5c74d924c03bb3500d740857bd49ca69cee752c5e100fa782 |
| 05 | [SILENT_PROTOCOL_PRODUCTION_B05.zip.part05](sandbox:/workspace/scratch/1c83c98bee20/silent_protocol_resume_20261008_2037/checkpoints/SILENT_PROTOCOL_PRODUCTION_B05.zip.part05) | 4e3c8e72962a16639c6ca3bec3b628749b8852f4c713bf979d41c402cb112203 |
| 06 | [SILENT_PROTOCOL_PRODUCTION_B05.zip.part06](sandbox:/workspace/scratch/1c83c98bee20/silent_protocol_resume_20261008_2037/checkpoints/SILENT_PROTOCOL_PRODUCTION_B05.zip.part06) | 4bc481c5773f4b523f08582593b21f90a8a8444e8db7e5d843c18ee09f6124ba |

校验清单、重组脚本、实际执行记录与音轨工作版：

- [SILENT_PROTOCOL_PRODUCTION_B05_REASSEMBLY.json](sandbox:/workspace/scratch/1c83c98bee20/silent_protocol_resume_20261008_2037/checkpoints/SILENT_PROTOCOL_PRODUCTION_B05_REASSEMBLY.json)
- [REASSEMBLE_B05.py](sandbox:/workspace/scratch/1c83c98bee20/silent_protocol_resume_20261008_2037/docs/REASSEMBLE_B05.py)
- [B05_EXECUTION.md](sandbox:/workspace/scratch/1c83c98bee20/silent_protocol_resume_20261008_2037/docs/B05_EXECUTION.md)
- [SILENT_PROTOCOL_MIX_WORKPRINT_v2_18M15S_FLAC_IN_MP4.m4a](sandbox:/workspace/scratch/1c83c98bee20/silent_protocol_resume_20261008_2037/output/SILENT_PROTOCOL_MIX_WORKPRINT_v2_18M15S_FLAC_IN_MP4.m4a)

将六个分卷、重组清单与脚本放在同一目录。在该目录运行：

    python3 REASSEMBLE_B05.py .

脚本会逐卷检查大小和 SHA256，拼接出 SILENT_PROTOCOL_PRODUCTION_B05.zip，并再次核验完整 ZIP 的 SHA256 与 CRC。已有同名 ZIP 时会停止，保护已有文件。解包时选择新的独立目录，保留原救援 ZIP 与 B04 检查点。

完整 ZIP：598,123,268 字节。SHA256：5caed769422c04362976c147c39fd0b5c10fcf7d68937f9bc31a7415b6193165。

本轮图像生成两条通道均实际受限：内置生成返回 429；备用服务图像提交也被额度限制拒绝，没有产生新图像。原前期完整工程重试仍为 403。正式合成实际前置检查因 E4 缺失而退出，没有生成空白或占位的正式成片。

图像工具报告北京时间 2026-10-08 22:42:02 重置；实际恢复仍须验证。没有后台运行保证，旧 Work 状态仍未知。

本轮已将六个已保存分卷全部重新下载并重组，完整 ZIP 的 SHA256 与 CRC 校验通过。首次末卷本地传输截断，重试取得完整末卷且哈希一致；首次失败副本保留。提供的重组脚本已经实际用于本轮六卷重组并验证通过。