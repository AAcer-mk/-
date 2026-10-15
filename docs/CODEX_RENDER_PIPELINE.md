# 可执行渲染管线

## 选择与范围

当前机器5 CPU、约33GiB内存、无可见GPU设备。已有Blender4.3.2、Godot4.6.3、Chromium及FFmpeg7.1.5。未发现Unreal安装；没有可调用的视频或配音生成接口。没有安装大型引擎或下载未经授权的角色资产。

主路径为Blender实体几何和物体/摄影机关键帧，Eevee通过软件图形回退实际渲染；Cycles CPU用于同场景比较。2D界面由原Noto字体和Pillow逐帧绘制，作为真实三维屏幕纹理。FFmpeg负责编码、2.39:1画面封装、原音轨符合和输出；它不生成三维场景。

| 方案 | 本次实测 | 选择 |
|---|---|---|
|Cycles CPU|基础960×402/16采样约0.72秒；实体风扇同规格约10.24秒/帧，低采样噪点明显；当前构建不含OIDN|可用，但不作为本机批量首选|
|Eevee软件渲染|复杂风扇960×402/16采样首帧18.39秒，含上下文/Shader初始化；1920×803/8采样首帧15.21秒；可实际输出|选作当前批量路径，逐场景复测后续帧耗时|
|Pillow界面+三维屏幕|真实字体、独立柱图/波形变化，摄影机有空间视角|屏幕和原生插镜|
|Godot/Chromium|Godot版本可用；Chromium已实际播放历史输出|Godot未做渲染性能比较；Chromium用作播放验证|
|Unreal/视频模型|未安装/无可调用接口|未运行，不声称已比较性能|

当前手部模型是粗略关节测试，形状与人物设定不符，不能用于正式演员镜头。机房样片验证空间与运镜，尚未匹配全套日内瓦美术。不得把技术样片接进最终时间线。

## 运行

```bash
cd /workspace/-
python3 -m venv /workspace/codex-runtime/venv
/workspace/codex-runtime/venv/bin/python -m pip install -r production/codex_pipeline/requirements.txt

# 查看具备实际实现的任务，而非把未知镜头自动变成占位片。
/workspace/codex-runtime/venv/bin/python production/codex_pipeline/pipeline.py \
  --source /workspace/silent-protocol-source next

# 比较连续空间、屏幕、交互、低照度及实体风扇。
/workspace/codex-runtime/venv/bin/python production/codex_pipeline/pipeline.py \
  --source /workspace/silent-protocol-source samples --width 640 --frames 24 --samples 8

# 连续完成已实现的F4-01、E7-07、F9-04：画面→解码→音轨符合→浏览器播放→下一镜。
/workspace/codex-runtime/venv/bin/python production/codex_pipeline/pipeline.py \
  --source /workspace/silent-protocol-source produce --width 1920 --samples 8
```

依赖Blender/FFmpeg/Git可执行程序；浏览器播放脚本需要本机已有Node Playwright模块和`/usr/bin/chromium`。有输出不代表正式通过：生成状态始终先停在`TECHNICALLY_VERIFIED_PENDING_CREATIVE_REVIEW`。审图、实际运动和声音的质量决定是否纳入正式制作。

## 可恢复状态与数据流

`镜头ID → 原时间线/资产 → 场景几何 → 物体与摄影机动画 → 原生帧 → 编码 → 原声轨符合 → 完整解码 → 浏览器播放 → 创作检查`

输出目录使用脚本、时间线、分辨率、采样、引擎、镜头的配置哈希。不同配置进入新目录。每个任务使用文件锁防止双写，原子JSON保存已验证帧哈希；中断后复用同指纹的完好PNG，校验失败即停止。Blender保存带动画的`scene.blend`，保留原始帧和PNG哈希。先写pending视频，成功解码后才启用目标文件。构建文件留在`output/`；Git保留精选视频、源场景、关键帧、全帧哈希和代码。

主线渲染为2.39:1活动画面，封装在1920×1080黑边容器中，24fps且不改原始帧区间。当前1920宽渲染的活动高度803像素；偶数的最终视频容器使用1080高，不把放大预览冒充原生1080渲染。

## 声音与QC

`conform_audio.py`按每视频帧2000个48kHz采样帧裁取原混音；E7优先使用R6的65秒分场音轨。MKV母版PCM逐字节与源窗口相符；AAC播放版另记为有损。原对白没有因画面更新就自动成为最终配音。

`audit_media.py`对媒体完整解码，检查真实帧数和2fps采样运动；估计全局仿射后记录剩余光流。指标不能证明动作真实，必须看联系图和实际视频。`browser_playback.cjs`通过短时本地HTTP服务在Chromium真实播放，记录结束、解码帧数、丢帧、时间进度和截图；服务只用于内部验证，播放结束即关闭。

未来整片必须重新测量END-03六秒零采样、九次闸刀、音画同步、字幕、身份连续性和开放结局。当前插镜验证不能代替整片验收。
