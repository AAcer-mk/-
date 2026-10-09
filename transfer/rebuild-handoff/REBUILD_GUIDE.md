# SILENT_PROTOCOL TAR 精确重建交接

## 核验结论

- 已核验原始 TAR：`SILENT_PROTOCOL_COMPLETE_B10_REBUILT.tar`，1,128,171,520 字节，SHA-256 `2f07d56ff635894e6792265e25abb3392b7896879e186c271e53407f52fc4e39`。
- TAR 含 905 个普通文件成员，全部为 POSIX USTAR；没有目录成员、PAX 扩展头或 USTAR prefix 字段。成员头中的 typeflag 为 `0`，mode 为 `0644`，uid/gid/mtime 均为 `0`。
- 成员顺序、每个成员的原始 512 字节头块、数据填充、成员路径/大小/SHA-256，以及归档尾部原始字节均保存在 `TAR_STRUCTURE.json`。所有成员数据填充为零。最后一个成员的数据区从偏移 1,128,162,304 开始，345 字节数据后补齐到 1,128,162,816；随后是 8,704 个零字节（17 个 512 字节块），归档结束于 1,128,171,520。
- 本地恢复目录中 905 个对应文件逐个与 TAR 内数据比对，大小和 SHA-256 全部相同。目录另有 1 个不属于 TAR 的临时文件；重建程序按结构清单只读取 905 个成员路径，会忽略它。
- 搜索了当前可用工作区中的脚本、Shell 命令、日志和说明，没有找到创建原 TAR 时实际运行的命令或日志。因此本交接不声称知道原始打包命令；重建使用已核验 TAR 的原始头块和尾部字节，避免依赖对打包器默认参数的猜测。

## 重建文件

- `rebuild_exact_tar.py`：只读源文件，校验每个成员大小与 SHA-256，写入结构清单中的原始头块、文件内容、原始数据填充和尾部字节；写后校验归档大小和完整 SHA-256。输出路径已存在时拒绝继续。
- `TAR_STRUCTURE.json`：完整结构清单。每个成员保存原始 header block（base64）、头字段、归档偏移、数据偏移、长度、SHA-256 和数据填充；还保存精确尾部字节。
- `inspect_tar_structure.py`：可选的只读检查器，需提供原始 TAR；会核对归档哈希并生成同格式结构清单。
- `REBUILD_TEST_RESULT.json`：本工作区实测结果。

## 使用方法

将 `rebuild_exact_tar.py`、`TAR_STRUCTURE.json` 放在同一目录。把恢复出的 905 个文件放在一个根目录下，保持这些文件相对 TAR 根的路径。例如文件 `art/candidates/C-01_v1.png` 应位于 `<恢复根目录>/art/candidates/C-01_v1.png`。

```bash
python3 rebuild_exact_tar.py \
  --source-dir /path/to/recovered-root \
  --output /path/to/new/SILENT_PROTOCOL_COMPLETE_B10_REBUILT.tar
```

输出必须是尚不存在的新路径。脚本不会改写源文件或结构清单，也不会删除失败时留下的输出。只有输出 `status: VERIFIED` 且同时报告预期字节数和 SHA-256，才能继续使用 TAR。执行前应确认恢复根目录确有清单中的全部 905 个路径。

## Luna B 的 +10,240 字节差异

报告中的差值等于一个 10,240 字节 TAR record。当前已核验归档的成员数据和尾部布局见上述偏移与清单。仅凭“比目标大 10,240 字节”不能确定 Luna B 输出的具体成因；可能是结束填充额外多写了一个 record，但需要比较 B 的产物尾部和本清单才能确认。精确重建脚本逐字节采用已保存的原始 header、数据填充和尾部，实测消除了该不确定性。

