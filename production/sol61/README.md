# 《静默协议》Sol 6.1 制作恢复 · R01

本目录继承完整原始导演执行稿及 B10 工程。原始迁移分支及 main 不作修改。制作分支为 `production/sol61-resume`，基点为 Claude 的交接提交 `56cee68766ea8c88a30e250586e020b55f829210`。

新增原图：E6-04 的第三监控候选，以及 E6-05 的三个双家庭监控候选。原图原始字节在 `payload/round-r01/` 的 TAR 分卷中，逐卷和逐文件 SHA-256 见 `state/artwork_manifest.json`。`state/generation_records.json` 记录完整提示词、参考关系和实际画面检查。分卷沿用仓库已验证的 393216 字节机制，不需要 Git LFS 或付费存储设置。

## 恢复与重现

```bash
python production/sol61/project/restore_payload.py artwork_manifest.json
python production/sol61/project/restore_sources.py
python production/sol61/project/render_e6_resume.py --revision v1
```

`restore_sources.py` 只下载制作输入对应的分卷，逐卷和逐成员核对 SHA-256。不会重建完整 TAR，不会覆盖不同内容的原文件。原源工程落在 `source-b10/`，新成果落在本目录；均不写入原迁移分支。三个来源分支的精确提交和 TAR 索引指纹见 `state/source_pins.json`。

首次画面生成与实际封装修复采用的命令为：

```bash
python production/sol61/project/render_e6_resume.py --revision v2 --assemble-only --picture-revision v1
```

如果已经恢复输出文件，上述脚本会核验并复用已存在的同版本文件。返工应使用新 revision。无损母版为 H.264 + FLAC 的 MKV；播放工作版为 H.264 + AAC 的 MP4。禁止把初次封装失败的 v1 CLEAN 容器用作影片。

## 制作范围和保留项

E6 字卡和 E6-01 到 E6-06 的原时间线合计 1087 帧 / 45.291667 秒。E6-09 另为 113 帧 / 4.708333 秒；不能把它直接拼到 E6-06 后面跳过情节。E6-07 抱枕投掷、盖住摄像头，以及 E6-08 复用该动作的真实电视慢动作回放仍未完成。Runway 当前工作区为 Free、零额度、无可用视频模型；没有购买额度或更改套餐。

屏幕文字由原 Noto 字体合成；E6-02 使用真实恢复的 Cody 客厅监控素材，E6-05 用实际查看过的双画面分界制作竖向信息流。热搜第一项只显示 `00:47:13`，最后一镜只显示 `00:47:12`，不增加解释。人物动作仍是静态源图的摄影运动与屏幕局部变化，不把它们说成视频模型生成表演。

声音复用已恢复并完整解码的 B10 工作混音，配音文本和字幕时间来自原 SRT。旧配音来源链、笑声表演、最终听感和全片同步尚未终验。未改对白、剧情、人物关系、结局或片尾署名。

旧 F5-v4 残缺证据原始字节仍在迁移 TAR；本轮重新读取确认无效，F5-v5 通过独立解码。F6 clean 与双语工作版通过独立解码、三帧目检，没有重复渲染。

本目录所有视频均为工作版，整片仍未完成。下一制作任务是 E6-07 → E6-08 → E6 65 秒完整段落验收；随后 F7 → E7 → F8 → E8 → F9 → E9 → END。正式终验还须修订 E1-07/E4-03、检查九屏九闸刀、Hale 异常、多语种声音和 END-03 的全黑及六秒绝对零采样。

## 本轮实际视频交付

`state/renders_manifest.json` 指向 `payload/round-r02/` 的 42 个分卷。恢复后可直接播放下列工作版，不需要重新渲染：

```bash
python production/sol61/project/restore_payload.py renders_manifest.json
```

- `output/E6_PART_A_WORKPRINT_v2_1080P_BILINGUAL.mp4`：45.291667 秒双语 H.264/AAC 工作版。
- `output/E6_PART_A_WORKPRINT_v2_1080P_CLEAN.mp4`：同一段无内嵌字幕的播放工作版。
- `output/E6_PART_A_WORKPRINT_v2_MASTER.mkv`：无损工作音频母版，2174000 个采样/声道，原 B10 区间帧数与采样长度完全匹配。
- `output/E6-09_SILENT_WORKPRINT_v2_1080P.mp4`：113 帧，独立镜头。实际 AAC 解码采样，包括末尾编码填充，全部为零。
- 八个独立画面段 `*_PICTURE_v1_1080P.mp4`，供后续 E6 完整合成复用。

技术记录见 `qa/E6_RENDER_v2.json`。AAC 的尾部编码填充分别为 976 / 304 个采样/声道，已单列，不能把它误认为严格无损采样长度；无损母版没有此填充。实际视频帧数与原时间线完全匹配。全片声音表演、最终连续性与电影创作验收仍待完成。
