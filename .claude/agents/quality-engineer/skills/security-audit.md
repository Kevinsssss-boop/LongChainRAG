---
description: 全栈安全审计：检查 API 密钥泄露、JWT 安全、SQL 注入、XSS、CORS 配置等安全隐患
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, PowerShell]
---

# Security Audit（安全审计）

对全栈项目进行安全扫描：**Python FastAPI 后端 + React TypeScript 前端**。

---

## 6 大检查类别

### 🔴 类别 1：敏感信息硬编码

**后端搜索**：
```bash
# Python 文件中的密钥、密码
grep -rn -iE "(api_key|secret|password|token|jwt_secret)\s*=\s*[\"'][^\"']+[\"']" backend/app/ --include="*.py"
# .env 文件检查
cat .env
```

**前端搜索**：
```bash
# TypeScript 中的硬编码密钥
grep -rn -iE "(api_key|secret|token)\s*[:=]\s*[\"']" frontend/src/ --include="*.ts" --include="*.tsx"
```

### 🔴 类别 2：注入漏洞风险

**SQL 注入**（后端）：
```bash
grep -rn -E "(execute\(|raw.*sql|text\(.*\+|f\".*SELECT)" backend/app/ --include="*.py"
```

**XSS**（前端）：
```bash
grep -rn -E "(dangerouslySetInnerHTML|innerHTML|eval\()" frontend/src/ --include="*.tsx"
```

### 🟡 类别 3：配置文件安全

```bash
# 检查 .gitignore 是否包含关键文件
cat .gitignore | grep -E "\.env|data/|node_modules|__pycache__"
```

### 🟡 类别 4：FastAPI 安全

**检查项**：
- CORS 配置是否过于宽松（`allow_origins=["*"]`）
- JWT 过期时间是否合理（默认 24h）
- 限流中间件是否启用
- 认证端点是否公开（/login, /register）
- Admin 端点是否有权限保护

```bash
grep -rn "allow_origins\|SECRET_KEY\|ACCESS_TOKEN\|rate_limit\|get_admin_user" backend/app/ --include="*.py"
```

### 🟢 类别 5：依赖包安全

```bash
cd backend && pip list --outdated 2>/dev/null
cd frontend && npm audit 2>/dev/null
```

### 🟢 类别 6：其他隐患

- Python `print()` 残留（可能泄露调试信息）
- 前端 `console.log` 残留
- 异常消息直接返回给客户端
- 文件上传类型限制

```bash
grep -rn "console\.(log|debug)" frontend/src/ --include="*.tsx"
grep -rn "print\(" backend/app/ --include="*.py" | grep -v "#\|__init__"
```

## 输出要求

```
╭─────────────────────────────────────╮
│    🔒 安全审计报告                  │
├─────────────────────────────────────┤
│  📂 项目：RAG 知识库问答系统        │
│  🎯 总分：XX/100                    │
│                                     │
│  发现问题：                          │
│  🔴 高危：X 个                      │
│  🟡 中危：X 个                      │
│  🟢 低危：X 个                      │
╰─────────────────────────────────────╯
```

**通行标准**：安全评分 ≥ 70 分，无 critical 级别问题。