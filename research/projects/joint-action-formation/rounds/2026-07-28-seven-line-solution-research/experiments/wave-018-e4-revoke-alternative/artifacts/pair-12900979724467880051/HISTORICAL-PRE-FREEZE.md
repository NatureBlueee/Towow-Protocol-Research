# Historical pre-freeze artifact

状态：`HISTORICAL / REJECTED AS STANDALONE FROZEN TRUTH`

此目录保留早期实际运行结果供审计，不再是 Wave 018 的正式 acceptance artifact。

Root post-final 检查发现两个 SQLite 主文件的 header 仍为 WAL mode，而 pair/root hashes
只绑定了主文件，没有把 `-wal/-shm` 作为 truth package 的一部分。即使 rows 已经
checkpoint，删除 companions 也不能把 WAL-mode 主文件改成独立 DELETE-journal 数据库。

因此：

- 此 pair 的功能结果可作为历史运行记录；
- 此 pair 不能证明 standalone frozen SQLite truth；
- 不得再以 ROOT-ACCEPTANCE 的正式 pair 引用；
- 当前正式 acceptance 见 `../../ROOT-ACCEPTANCE.md` 指向的新 backup-frozen pair。

