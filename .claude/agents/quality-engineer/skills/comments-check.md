---
description: 检查代码注释质量：覆盖 Python + TypeScript/React，评估注释覆盖率、内容匹配度、可读性
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# Comments Check（注释质量检查）

对全栈项目代码进行注释质量审查。

---

## 3 大检查维度

### ① 注释覆盖率（够不够？）

目标 ~30% 注释率（3行注释:7行代码）

**Python 必须有的注释**：
- 函数 docstring（功能、参数、返回值）
- 复杂逻辑处内联注释
- 类/模块顶部说明

**TypeScript 必须有的注释**：
- 组件顶部 JSDoc
- Props 接口说明
- 复杂 hooks/副作用注释

### ② 内容匹配度（对不对？）

- 🔴 注释说的 ≠ 代码做的
- 🔴 过时注释（代码改了注释没改）
- 🟡 注释过于笼统

### ③ 可读性（看得懂吗？）

**好注释** ✅：
```python
def calculate_avg_price(products: list) -> float:
    """计算商品平均价格。空列表返回 0。"""
```

```typescript
// 把流式返回的文本片段拼起来，等 AI 说完后一次性存到消息列表
useChatStore.getState().finalizeStream();
```

**差注释** ❌：
```python
result = process(data)  # process data
```

## 执行方式

```bash
# Python 注释统计
find backend/app -name "*.py" | while read f; do
  total=$(cat "$f" | wc -l)
  comments=$(grep -c "^[[:space:]]*#" "$f" 2>/dev/null || echo 0)
  echo "$(basename $f): $comments / $total lines"
done

# TypeScript 注释统计
find frontend/src -name "*.ts" -o -name "*.tsx" | while read f; do
  total=$(cat "$f" | wc -l)
  comments=$(grep -cE "^\s*//|^\s*/\*" "$f" 2>/dev/null || echo 0)
  echo "$(basename $f): $comments / $total lines"
done
```

## 输出要求

各文件注释率统计表格，问题清单（文件:行号），改进建议。

**评级**：≥30% ✅优秀 | 20-29% ✅良好 | 10-19% ⚠️一般 | <10% ❌不足