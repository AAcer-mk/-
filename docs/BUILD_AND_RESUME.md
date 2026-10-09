# 静默协议：构建与续作

## 当前性质

这是 2026-10-08 正式制作重启后的真实工程检查点，不是完成电影。原始创作稿已完整读取并保留。主时间线为 1095 秒、24 fps、26280 帧、152 个时间线段落，其中 140 个摄影镜头。原抢救包保留为只读基线；所有修改发生在新的派生目录。

## 当前障碍

Imagegen 实际返回 HTTP 429、`usage_limit_reached`，套餐标识为 plus。工具报告的重置时间为 2026-10-08 14:42:02 UTC / 北京时间 22:42:02；该时间不保证重置后工具一定可用。Runway 当前账户余额为 0，视频生成不能作为当前可直接使用的替代。没有购买额度或更改套餐。

剩余缺失候选见 `project/RESUME_IMAGE_QUEUE.json`，共 161 个。原生成队列在六个额度错误后结束，没有宣称生成仍在后台进行。新工程等待素材的渲染队列已主动中断，工具返回退出码 130。旧 Work 执行状态仍未知，本工程不访问旧任务可写路径。

## 源文件和保存

- 原始完整执行稿：`docs/ORIGINAL_CREATIVE_BRIEF.txt` / `.md`。
- 原恢复基线 SHA256：`3a7c369b9e16bbd4bf2a850ac068cae86105442ab883e36a0d9ceda5dbc245d5`。
- 最新源工程检查点：`SILENT_PROTOCOL_PRODUCTION_B03_SOURCE_CHECKPOINT.zip`。它包含当前全部画面源、图形、参考、音轨、脚本、字幕、日志和检测证据，不包含单独保存的渲染 MP4，也不包含公开可重新下载的 ASR 模型或软件安装目录。
- 原损坏 PNG 的证据副本：`evidence/E9-07_v2_TRUNCATED_original.png`。原文件和基线 ZIP 未覆盖。派生修复图在 `graphics/native_candidates/E9-07_v2.png`；它仍需在 E9-01 生成后核对公寓与人物连续性。
- 当前两个 425 秒工作版单独保存，文件名明确含 `WORKPRINT`。它们不能替代正式成片。

## 可复现构建

在独立目录解包源工程后安装 Python 3.12、ffmpeg 6.1.1 或兼容版本，以及 `project/requirements-render.txt` 中的依赖。实际运行版本见 `project/runtime_versions.json`。

```bash
python3 -m pip install -r project/requirements-render.txt
python3 project/build_timeline.py
python3 project/rebuild_manifest.py
python3 project/film_compositor.py E4
python3 project/assemble_film.py --full
```

每段渲染前要求三个实体图像候选实际存在且可解码；缺失时抛错，不替换为空白或其他镜头。渲染完成后自动执行 ffprobe 与完整解码检查。`assemble_film.py --full` 要求全部段落 MP4 存在，否则中止。当前不满足这一条件，未执行整片渲染。

为了保护已有输出，脚本拒绝覆盖既有目标；返工时先在脚本中采用新的修订文件名。不要把旧版本删除后重跑。

```bash
python3 project/final_audio.py
python3 project/checkpoint.py SCENE_REVISION_LABEL
python3 project/package_checkpoint_volumes.py SCENE_REVISION_LABEL
```

`final_audio.py` 从原音轨建立派生混音，替换测得的九次闸刀瞬态，使用一个固定原创建模声源和递增混响，保存独立 WAV 声源与九个效果文件，再检验 FLAC 解码、采样数、削波与六秒全零。已生成的 v2 文件不要覆盖；新修订需新名称。

字幕 SRT 保持中英双语。合成脚本从 SRT 生成 ASS，以真实 Noto 字体合成中文在上、英文在下的内嵌字幕。

## 正式续作顺序

1. 重新读取原稿和 `assets_manifest.json`，确认基线及检查点哈希；不要重新设计剧情或人物。
2. 检查生成额度或其他已授权工具的实际可用性。只执行 `RESUME_IMAGE_QUEUE.json` 中缺失项，并按原日志中的角色、场景参考和分镜生成。
3. 返工 E1-07 的多城市、多人物蒙太奇；目前选用候选仍需身份与地点修订。E4-03 需表现加班族反应，不能只聚焦小满。机房宽景需检查九块屏幕及九道闸刀的数量与断电连续性。
4. 不对非分格画面直接做四象限蒙太奇裁切。根据真实候选构图制作有意义的切点。
5. E9-01 到位后重建镜像画面，并核对韩语声音从一秒延迟、半秒延迟到同步的关系。
6. 完成剩余片段、全片、仅取 C/E1/E5/E9 的正式 30 秒预告。原预告保留为工作版，未升级为正式交付。
7. 对实际完整成片检查字幕、画面连续性、所有文字、九次音效、符号彩蛋、六秒黑场及静音、开放结局、片头片尾和来源清单。AAC 等有损编码之后必须重新测量六秒采样；FLAC 验证不能替代成片验证。
8. 每段完成后更新清单并保存检查点，最后保存全部正式交付。未运行或仍有问题的测试保持待验。

## 自动转写证据

`qa/dialogue_asr_evidence.jsonl` 和 `dialogue_asr_summary.json` 来自对实际解码音轨的 54 段转写。英语、中文、日语和韩语均有识别证据；自动转写不能代替听感和表演质检。西语短句置信度较低，阿拉伯语、德语等叠加声部未确认，须继续核对。

复查脚本为 `project/verify_dialogue.py`；本轮使用 faster-whisper 1.2.1、CTranslate2 4.8.2、small 多语模型、CPU int8。ASR 工具和模型仅用于检查，没有将真人音频作为声音生成参考。