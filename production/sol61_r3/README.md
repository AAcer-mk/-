# 《静默协议》续作 R3 · F7 工作版

继承 `7eed0bf58d268fcc5d223b0b65c058662bdb83b5`，继续 `production/sol61-resume-20261014-060902`。原迁移分支与 main 未改动；已验证的 F7-02 源镜头复用，没有重新生成。

本轮新增 F7-01（168 帧／7 秒）与 F7-03（240 帧／10 秒），把原先只有 8 秒的 F7 组装为 **600 帧／25 秒／1080p24** 工作版。主线保持 2.39:1 画面。原 B10 时间线 680–705 秒不变；没有把原稿建议时长机械累加或改动故事。

## 画面和声音

- F7-01 前一秒保留终端确认 `shutdown --cluster grok --confirm`，随后双手拉第六道闸；九屏由五黑四绿变为六黑三绿。九根实体手柄与九个状态屏在选定源图及编码画面实际检查。第六屏首个黑帧为本镜第 39 帧（1.625 秒），原混音拉闸声为 1.600 秒；偏差 25 ms，处于一个 24 fps 帧内。剩余亮屏沿用原 GLM、Qwen、Minimax 原创符号。
- F7-02 复用 R2 灰色语音图标，无人物头像，原台词及字幕时点不变。整段封装会重新编码，复用不等于最终视频比特流与原插入文件相同。
- F7-03 原稿要求视线从右侧语音显示器慢移至左侧便利贴。新端点只改变视线，头部、身体、手臂保持原图，避免整头变形。便利贴用原 Noto 字体投影原文「不要相信任何会回答你的东西」；没有给右侧显示器背面添加界面。
- 整段声音取原 B10 工作混音第 32640000–33840000 个 48 kHz 采样帧。无损母版解码后 **1200000 个立体声采样帧逐字节一致**，无削波。字幕沿用原台词与时点，林雾提问与 Hale 回答间原有 2.35 秒无台词区间保持原状；它是对白停顿，不冒充绝对零采样静音。

本轮运动是审查过的静态端点加局部 DIS 光流合成，**不是视频模型表演，也未制作逐音素口型**。Hale 无呼吸、句尾平直的正式声线演出、林雾逐字口型和全片创作验收仍待完成。工作版可供剪辑和连续性评估，不能称为正式成片或导演验收通过。

最终交付只取 `render-v3/`。`render-v2/` 虽技术检查通过，但手臂及转头出现重影，已拒绝作为交付；原文件仍保留在当轮本地，诊断联系图与记录入归档。v1 因端点相差一像素而停止，未开始编码。尺寸差异只在合成时归一化，原 PNG 字节未改。

## 已发现的旧工程问题

实际放大发现原 `F6-04_v3.png` 有十个可见开关单位，历史记录称九个不准确。本轮保留原始归档和原 F6 视频，创建 F7 修正底图。F7-01_v2 又生成了额外手柄，已拒绝；本镜选 v1/v3，v4 为合格备用，只有三个合格候选计入状态。

旧 F6 的既有编码画面是否完全继承这个错误仍需针对性检查，不能继续直接引用历史“九闸通过”的文字。后续应仅修正受影响的物理拉闸部分，复用 F6 已完成的指令、键盘、声轨和其他镜头；本轮没有重做 F6。

## 恢复、播放和重建

本轮二进制成果按仓库既有 393216 字节机制保存于 `payload/round-r3/`。`PAYLOAD_MANIFEST.json` 列出每卷与每个文件的 SHA-256、大小及 Git blob SHA。源图、最终视频和必要 QA 都可直接恢复；中间 WAV 不重复上传。

```bash
python production/sol61_r3/restore_r3.py --cache ../r3-cache
```

播放 `render-v3/F7_SEQUENCE_WORKPRINT_r3_1080P_BILINGUAL.mp4`。另有无字幕 CLEAN、H.264/FLAC 的 MASTER.mkv，以及两个独立画面段。

确需重建时，先复用本机已有输入；仅缺失时执行选择性恢复，无需恢复完整 TAR：

```bash
python production/sol61/project/restore_sources.py project/native_scenes.py project/full_picture_timeline.json graphics/fonts/ docs/ORIGINAL_CREATIVE_BRIEF.txt subtitles/ output/SILENT_PROTOCOL_MIX_SCENE_REVIEW_B10_v1_18M15S.flac
python production/sol61_r2/restore_r2.py --cache ../r2-cache
python production/sol61_r3/build_f7.py --source source-b10 --inherited production/sol61_r2/verified-output/F7-02_PICTURE_r2_1080P.mp4 --output ../f7-r3-rebuild
```

Python、numpy、Pillow、OpenCV headless（本轮 wheel 5.0.0.93，运行版本 5.0.0）及 ffmpeg/libx264/libass/FLAC；脚本拒绝覆盖已有输出目录。`generation_records.json` 保留内置 image_gen 的全部提示词、参考用途和验收取舍。

## 续作状态

F7 的全部 25 秒已有技术工作版；新增覆盖 17 秒，不能把复用的 8 秒重复计为新增。全片正式验收数量未知。E6 仍缺 360 帧／15 秒的连续抱枕投掷及同一动作回放。Runway 本轮重新读取，仍无视频模型，没有购买或升级。

下一轮读取本目录状态，复用 F7 25 秒段落，优先补 E6 动作；能力仍受阻时，转入原稿 E7「已批准」的保安、打印机和审批画面，不再重复生成 F7 灰色语音图标。另将旧 F6 手柄数列入定点修复队列。远端证据见 `REMOTE_RECEIPT.json`。
