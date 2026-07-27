# Local Codex Workspace Smoke Task

你正在进行一个最小、只读的本地执行验证。你本身就是直接运行在该工作区中的本地 Codex Agent。

## 允许动作

1. 读取当前工作目录和 Git 元数据。
2. 读取 `AGENTS.md`、README 和构建/测试配置名称，用于发现命令。
3. 运行无害的版本、状态和测试发现命令。
4. 创建且仅创建一个结果文件：

```text
.ai-research/towow-a2a-r5/smoke/CODEX_LOCAL_SMOKE_RESULT.json
```

## 禁止动作

- 不修改项目源文件；
- 不安装依赖；
- 不运行生产服务；
- 不 push、commit、reset、stash 或改动用户已有修改；
- 不打印秘密；
- 不把“能读取工作区”误写成“已经完成真实研究实验”。

## 必需结果 JSON

```json
{
  "status": "success|failed",
  "timestamp_utc": "...",
  "cwd": "...",
  "repo_root": "...",
  "git_head": "...",
  "git_branch": "...",
  "git_dirty": true,
  "codex_environment": {
    "agent": "...",
    "model": "...",
    "cli_or_app_version": "...",
    "version_source": "command|environment|unknown"
  },
  "agents_files": ["..."],
  "discovered_test_commands": ["..."],
  "commands_run": [
    {"command": "...", "exit_code": 0}
  ],
  "source_files_modified": [],
  "notes": "..."
}
```

只有文件存在、内容与实际命令输出一致、且项目源文件没有变化时，smoke 才成功。
