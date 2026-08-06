---
description: 为当前项目创建单元测试（Pytest + Vitest 双栈），编写测试代码、执行测试并生成测试报告
allowed-tools: [Bash, PowerShell, Read, Write, Edit, Glob, Grep]
---

# Unit Test

为当前全栈项目创建和运行单元测试，后端使用 **Pytest**，前端使用 **Vitest**。

---

## 前置知识

- **单元测试** = 给代码写"考卷"，自动检查代码有没有 bug
- **Pytest** = Python 测试框架，用 `assert` 做断言
- **Vitest** = 前端测试框架，兼容 Jest API

---

## 完整流程

### 第 0 步：环境检查

**后端**：
```bash
pip list 2>/dev/null | grep pytest
```

**前端**：
```bash
cat frontend/package.json | grep -E "vitest|@testing"
```

---

### 第 1 步：后端测试

#### 1.1 确认 Pytest 配置

检查 `backend/pytest.ini` 是否存在，如不存在则创建。

#### 1.2 分析后端代码

```
优先级：
🔴 高：core/security.py, rag/splitter.py, rag/retriever.py, schemas/
🟡 中：api/auth.py, api/session.py, services/cache_service.py
🟢 低：models/, config.py, main.py
```

#### 1.3 编写后端测试

测试文件放在 `backend/tests/` 下，命名 `test_*.py`。

```python
import pytest
from app.core.security import hash_password, verify_password

class TestHashPassword:
    def test_hash_returns_string(self):
        result = hash_password("password123")
        assert isinstance(result, str)

    def test_verify_correct_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True
```

#### 1.4 执行后端测试

```bash
cd backend && python -m pytest tests/ -v --tb=short
```

---

### 第 2 步：前端测试

#### 2.1 确认 Vitest 配置

检查 `frontend/vitest.config.ts`。

#### 2.2 分析前端代码

```
优先级：
🔴 高：store/*.ts, api/chat.ts, utils/*
🟡 中：components/Chat/*, components/Knowledge/*
🟢 低：pages/*, components/Layout/*
```

#### 2.3 编写前端测试

```typescript
import { describe, it, expect } from 'vitest';
import '@testing-library/jest-dom/vitest';

describe('ChatStore', () => {
  it('should add messages', () => {
    useChatStore.getState().addMessage({...});
    expect(useChatStore.getState().messages).toHaveLength(1);
  });
});
```

#### 2.4 执行前端测试

```bash
cd frontend && npx vitest run
```

---

### 第 3 步：生成测试报告

```bash
# 覆盖率
cd backend && python -m pytest tests/ --cov=app --cov-report=term
cd frontend && npx vitest run --coverage
```

---

### 第 4 步：写入门禁标记

写入 `.claude/check-results/test-result.json`。

---

## 注意事项

1. 不要测试 `main.py`（FastAPI 入口）和 `main.tsx`（React 入口）
2. Mock 外部 API 调用（llm、embedding）
3. 测试文件放在源码同目录下
4. 每个测试用例独立
5. 如果用户中途取消，保留已创建的测试文件