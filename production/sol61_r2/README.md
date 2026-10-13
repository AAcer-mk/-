# 《静默协议》Sol 续作 R2

继承提交 `d61c38c91107b154b8c33b6bd31f74ac2207b1ce`，继续同一独立分支 `production/sol61-resume-20261014-060902`。所有历史工程分支和 main 保持原状；未重建完整 TAR。

## 实际成果

- **F7-02**：灰色语音图标镜头，192 帧／8 秒／1080p24，无人物头像。原台词「很好。还剩三个。你做得很好，林雾。」及双语字幕准确接入原 687–695 秒区间。母版 FLAC 与原 B10 工作混音选定 384000 个立体声采样帧完全一致。新增可用画面覆盖为 8 秒；声线的无呼吸和句尾平直表演仍待听审，不能称为导演终验通过。
- **E6 前段修订**：字卡至 E6-06，1087 帧／45.291667 秒。复用五个既有画面段，接入上轮本分支的 E6-02 手机直播和 E6-06 热搜画面。声音继续使用原 B10 工作混音，2174000 个立体声采样帧逐样本一致。没有跳过 E6-07/08 拼接结尾；本项是现有 45 秒的整合修订，不计新增时长。
- **E6-07 三张动作源图**：同一 Cody、灰 T 恤、灰沙发、左条纹抱枕、右锈色几何抱枕及蓝光客厅。三张均为起身准备投掷的静态候选，未完成投掷／遮挡。默认优先 v2（投掷目标摄像头可见、两手抓握清楚）；v3 是更紧的备选构图，摄像头在画外。完整提示词与参考关系在两份 generation record 中，使用内置 image_gen 生成。

六个声音工作版均完整解码通过，准确帧数、分辨率、24/1 帧率和字幕位置已验证，无削波；两份无损母版均与原混音 PCM 一致。AAC 播放版存在正常编码填充，单列于 QA，不称为逐样本无损。实际解码联系图已经查看。初次 MKV→MP4 直接复制导致时间戳量化偏差，失败媒体仅在当轮本地诊断目录 `output/`，不得用于交付；已改为重建 CFR 时间戳及 24000 Hz MP4 时间基，最终文件只取 `verified-output/`。

## 二进制恢复和复现

本轮最终源图、视频、字幕、解码 QA 图和技术检查通过确定性 TAR 分卷保存，沿用仓库 393216 字节机制。`PAYLOAD_MANIFEST.json` 固定每卷与每个文件的大小、SHA-256 和 Git blob 身份。中间提取 WAV 未重复归档，原混音已有可信归档。

在仓库根目录恢复本轮成果：

```bash
python production/sol61_r2/restore_r2.py --cache ../r2-verified-cache
```

无需渲染即可播放 `verified-output/E6_PART_A_WORKPRINT_r2_1080P_BILINGUAL.mp4` 或 `verified-output/F7-02_WORKPRINT_r2_1080P_BILINGUAL.mp4`。无字幕播放版以 CLEAN 结尾，无损音频工作母版以 MASTER.mkv 结尾。

如确实需要重建，先复用已在当前机器上的 `source-b10/` 和继承画面。缺失输入才执行以下选择性恢复；没有全量 TAR 重建：

```bash
python production/sol61/project/restore_sources.py
python production/sol61/project/restore_payload.py renders_manifest.json
python production/sol61_r2/build_continuation.py --source source-b10 --peer production/sol61/output --screens production/sol61_060902/output --output ../r2-rebuild
```

构建脚本拒绝覆盖已有目录。Python、numpy、Pillow、ffmpeg/libx264/libass/FLAC 和原 Noto 字体即可；没有新增模型下载依赖。

## 当前状态与具体续作点

E6 可用画面覆盖仍为 1200／1560 帧（50 秒）；缺 E6-07/08 的 360 帧／15 秒连续投掷及真实慢放。本轮候选图使 E6-07 由无源图推进至有三份静态源图，不能计为完成动作。Runway 实时复核仍为无可用视频模型，未购买或升级。

F7 已单独形成 F7-02 工作版，其余 F7-01 拉第六闸、三块亮屏和 F7-03 林雾转向便利贴仍缺；不能称为完成 25 秒 F7。全片导演验收数量仍未知。Hale 无头像、异常不揭晓、原叙事、九闸顺序和结局未修改。

下一步优先用 `assets/E6-07_v2.png` 制作足额连续动作，经实际逐帧查看确认投掷轨迹与镜头遮挡后，将同一动作接入 E6-08 的电视慢放及两个错开圆点，补笑声突然停止和一秒静音，再接已验证 E6-09。动作能力继续受阻时，可接着生产 F7-01/F7-03，复用本轮 F7-02，严格保持其原时间边界。

远端保存证据在 `REMOTE_RECEIPT.json`；该文件列出的成果提交为二进制数据提交，后续文档提交可能使分支 HEAD 更靠后。
