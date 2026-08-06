---
description: 用 Git 进行存档（提交 + 推送到远程），自动检测变更并引导填写提交信息
allowed-tools: [Bash, PowerShell, Read, Write, Glob]
---

# Git Save

用 Git 进行存档（commit + push）。

## 流程

### 第 1 步：检查状态

```bash
git status
git diff --stat
```

### 第 2 步：确认提交信息

根据变更内容，帮用户生成建议的提交信息。

格式：`存档 N: 描述内容`

### 第 3 步：执行提交

```bash
git add -A
git commit -m "COMMIT_MESSAGE"
```

### 第 4 步：推送到远程

```bash
git push origin master
```

> 如果推送失败（如没配置 remote），告诉用户推送失败但不影响本地存档。