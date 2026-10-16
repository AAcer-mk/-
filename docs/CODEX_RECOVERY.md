# Codex 恢复说明

工作分支：`codex/animation-pipeline-20261015`，继承`7fbcaebba95371d6f7cb16bb75a7b8f6e29c1edb`。使用已有检出目录，不新建Git worktree。全部迁移分支只读；不要reset、覆盖或删除历史素材。

## 已执行的恢复

通过现有Git HTTPS代理取得全部迁移Git对象，无需额外令牌。`production/codex_pipeline/recover_git.py`固定不可变提交，从Git Blob读取每个切片，逐片验证长度/SHA；流式拼为唯一临时TAR，验证完整长度/SHA，再核对结构清单及905个成员。不会保留第二份完整TAR或展开每个迁移分支。

```bash
cd /workspace/-
git fetch --filter=blob:none origin '+refs/heads/*:refs/remotes/origin/*'
# 首次缺少大部分对象时，批量获取比逐片懒加载快；已缓存时跳过这一命令。
git -c fetch.negotiationAlgorithm=noop fetch --refetch --no-filter origin \
  production/sol61-resume-20261014-060902 \
  migration/luna-a-tail-rescue-1087-1283 \
  migration/luna-b-1284-2076 migration/luna-c-2077-2870
python3 production/codex_pipeline/recover_git.py \
  --repo /workspace/- --source /workspace/silent-protocol-source \
  --receipts /workspace/-/production/codex_pipeline/qa/recovery
python3 production/sol61/project/restore_payload.py artwork_manifest.json renders_manifest.json
```

`recover_git.py`同时恢复R2–R6的186成员；两个Sol61旧payload另恢复16成员。与已存在文件逐字节哈希对比，相同内容复用，不同内容拒绝覆盖。原始恢复根在`/workspace/silent-protocol-source`，不写入旧绝对路径。重新执行恢复只作验证/缺失补齐，不重新生成素材。

三段切片提交：

| 原包切片范围 | Git提交 |
|---|---|
|1–1283|`caa6662db7b695c4ca91740a2840ae603bf0f5f5`|
|1284–2076|`887232f3456c8ce132ca98d688e6413863b0575d`|
|2077–2870|`ddceabc7c15f550a2705ca38068006bdf41dad87`|

完整TAR：1,128,171,520字节，SHA-256 `2f07d56ff635894e6792265e25abb3392b7896879e186c271e53407f52fc4e39`。全部2870片和905成员在本次实际通过。JSON证据在`production/codex_pipeline/qa/recovery/`。

## 坏文件与复用

`qa/EXCLUDED_MEDIA.json`记录本次不能解码的4张图片、3个音视频。它们均保留原文件；F5使用后续有效工作版，不使用`F5_picture_clean_v4_1080p.mp4`。不能因哈希与归档一致就把损坏文件当可播放素材。

已有R2–R6母版、混音和源图片保留在原目录。恢复出的未跟踪二进制由其既有payload保存，不重复提交；`.gitignore`只排除这些派生/恢复目录和本轮渲染缓存。新精选交付保存在`production/codex_pipeline/deliverables/`。

## 会话恢复

读取`production/PROGRESS.json`、`production/SHOT_AUDIT.json`和`docs/CODEX_PRODUCTION_STATUS.md`。检查实际文件和哈希，不能假定进程跨会话存活。没有用户需要反复发送“继续”的阶段锁；有可执行任务就继续，具体阻断必须写入状态。

## 本轮环境配置与生产账本

`bash production/codex_pipeline/cloud_setup.sh`已在当前工作区实际运行通过：渲染/声音两个隔离环境的`pip check`、六项恢复保护检查、模型大小及SHA-256、Node Playwright与Chromium可用性均通过。首次缺少原资产时才获取固定提交并恢复，已存在的原资产和权重直接复用。当前验证不等于在新任务中验证了快照恢复。

`refresh_progress.py`重新核对已交付文件的每个大小/SHA-256、完整解码/原声符合与实际播放回执；通过文件锁区分当前活跃渲染与陈旧的RENDERING状态。`--export-completed`只导出已经完成音轨符合与实际播放的新镜头，不覆盖既有交付。

```bash
/workspace/codex-runtime/venv/bin/python production/codex_pipeline/refresh_progress.py --export-completed
/workspace/codex-runtime/venv/bin/python production/codex_pipeline/render_native_cards.py --source /workspace/silent-protocol-source
```

独立对象库已从GitHub重新读取提交`139fb56365d5c1b225d856031a26a76ec9b651c6`的374个交付文件，共117,014,918字节，全部与本地SHA-256一致；证据见`qa/REMOTE_PRODUCTION_SHOTS.json`。这验证远端字节保存，不代表新会话安装或影片终验。
