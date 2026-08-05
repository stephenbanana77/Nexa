---
name: nexareviewer
description: Nexa 项目代码审查。检查提交前的代码变更是否符合 10 条生产级标准（认证、错误处理、类型安全、分页、注入防护、配置、并发安全）。仅对 git diff 范围内的代码运行，不审计全库。触发词：review、code review、审查、检查代码。
agent_created: true
---

# Nexa Code Reviewer

## 目的

在每次提交前对 `git diff` 范围内的代码进行快速审查，对照 Nexa 项目 10 条生产级标准逐条检查，输出通过/不通过及修复建议。

## 使用方式

### 步骤 1：获取变更范围

```bash
git diff HEAD~1 --name-only     # 最近一次提交的变更文件
git diff --cached --name-only   # 暂存区的变更文件
```

仅审查 `.py`、`.ts`、`.tsx`、`.js`、`.json`、`.yml` 文件。跳过 `dist/`、`node_modules/`、`venv/`。

### 步骤 2：逐条检查

加载 `references/checklist.md`，对每个变更文件逐条验证。每条检查结果分为：✅ 通过 / ❌ 失败 / ➖ 不适用。

### 步骤 3：输出报告

```markdown
## Review Report

| # | 检查项 | 结果 | 文件 | 说明 |
|---|--------|------|------|------|
| 1 | Auth | ✅ | - | 所有新端点已添加 get_current_user |
| 2 | Error | ❌ | chat.py:42 | catch 块未记录日志 |

**总结**: X 通过 / Y 失败 / Z 不适用
```

## 规则

- 仅检查变更文件，不审计全库
- 如果变更仅涉及文档或配置文件，标记所有代码检查为 ➖
- 对 ❌ 项提供具体的修复代码
- 如果所有关键项（1-6）都通过，标记为 "Ready to push"
