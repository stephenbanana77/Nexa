# Nexa V0 UI Spec

Version: 1.0
Status: Confirmed

---

## 1. Design Philosophy

- 不追求"AI 感"，追求"专业工具感"
- 黑白灰为底，强调色点到为止
- 让数据本身成为视觉主角
- 每一次交互都是可理解的，不要黑箱

---

## 2. Color Palette

| Token | Value | Usage |
|-------|-------|-------|
| Background | `#141414` | 页面底色 |
| Surface | `#1a1a1a` | 卡片、面板 |
| Surface Elevated | `#1f1f1f` | 指标卡片、选中态 |
| Text Primary | `#ddd` | 主要文字 |
| Text Secondary | `#888` | 次要文字 |
| Text Tertiary | `#666` | 辅助信息 |
| Border | `#333` | 分割线、边框 |
| **Accent** | **`#2563EB`** | 强调色（标签、链接、进度） |
| Accent Light | `#60a5fa` | 悬停态、类型标注 |
| Danger | `#ef4444` | 错误、缺失率告警 |
| Success | `#22c55e` | 完成状态 |
| Warning | `#d29922` | 运行中状态 |

---

## 3. Layout Structure

### Global Layout

```
┌─────────────────────────────────────────────┐
│  Top Bar: [项目名]  [Chat] [Data] [Insights] │  ← 深色 (#1a1a1a)
├─────────────────────────────────────────────┤
│                                             │
│           Content Area                       │  ← 页面底色 (#141414)
│                                             │
└─────────────────────────────────────────────┘
```

- 侧边栏不做——V0 页面少，顶部 Tab 导航够用
- 顶部 Bar 左边显示当前项目名，右边显示页面 Tab
- 当前激活的 Tab 用强调色 #60a5fa，非激活的用 #777

### Project Workspace Tabs

| Tab | 优先级 | 说明 |
|-----|--------|------|
| Chat | P0 | 默认着陆页，AI 对话分析 |
| Data | P0 | 数据 Schema 和预览 |
| Insights | P0 | 保存的分析结果 |
| SQL | P1 | 高级用户的 SQL 编辑器 |
| Notebook | P1 | 混合编辑环境（Markdown/SQL/Python） |

---

## 4. Home Page

### Components

- 顶部：Logo + "Your AI Data Analyst" + [New Project] 按钮
- 主体：Recent Projects 卡片网格
  - 每张卡片：项目名 / 数据集名+行数 / 更新时间
  - 最后一张卡片为虚线边框的 Create Project 入口

---

## 5. Chat Page

### Message Styles

**用户消息：**
- 灰色圆形头像（首字母）
- 浅灰底气泡，圆角 8px

**Nexa 响应（静态）：**
- 科技蓝圆形头像（N）
- 深灰底气泡，带微边框

**Nexa 响应（分析进行中）：**
- 三步状态指示器替代进度条

### SSE Progress Indicator

```
Understanding intent  ······  done    ← #22c55e
Querying 120K rows    ······  running ← #d29922 + 脉冲动画
Generating charts     ······  pending ← #484f58
```

- 每个步骤一行：指示圆点 + 描述 + 状态标签
- done：绿色圆点 + 绿色标签
- running：琥珀色圆点（脉冲动画） + 琥珀色标签
- pending：灰色圆点 + 灰色标签
- 分析完成后，进度指示器替换为最终分析结果

### Chat Actions

分析结果卡片底部：
- [Save Insight] —— 保存到 Insights 页
- [Open in Notebook] —— 跳转到 Notebook，自动填充 Markdown/SQL/Python cell

---

## 6. Data Page

### Components

**指标卡片行（3 列）：**
- Dataset 名称（左，较宽）
- Rows 数量（中）
- Columns 数量（右）
- 背景 #1f1f1f，无边框

**Schema 表格：**
- 列名 / 类型 / 缺失率
- 类型列用强调色 #60a5fa
- 缺失率 > 10% 用红色 #ef4444

**Data Preview：**
- 使用 ag-grid-community（虚拟滚动）
- 默认展示前 1000 行
- 底部标注 "Showing 1,000 of N rows"

---

## 7. Insights Page

### Layout

卡片列表，每张 Insight Card 包含：
- 原始问题（加粗）
- 分析摘要（一行）
- 图表缩略图（如果有）
- 创建时间

点击卡片展开完整内容：
- Summary
- Key Findings（列表）
- Charts（交互式 ECharts）
- SQL Queries（代码块）
- Recommendations（列表）

---

## 8. SQL Page

### Components

- 左侧：SQL 编辑器（深色主题，等宽字体）
- 右侧：AI SQL 生成入口（自然语言 → SQL）
- 底部：查询结果表格（ag-grid）
- 执行按钮 + 执行状态

---

## 9. Notebook Page

### Cell Types

按 Jupyter 风格垂直堆叠：

1. **Markdown Cell** —— 编辑/预览切换
2. **SQL Cell** —— 编辑器 + 执行按钮 + 结果表格
3. **Python Cell** —— 编辑器 + 执行按钮 + 输出区域

### Chat Bridge

从 Chat "Open in Notebook" 跳转时，自动创建 Notebook：
- Cell 1 (Markdown)：分析上下文说明
- Cell 2 (SQL)：AI 生成的 SQL
- Cell 3 (Python)：ECharts 配置代码

---

## 10. Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Page Title | System sans | 15px | 500 |
| Card Title | System sans | 14px | 500 |
| Body | System sans | 13px | 400 |
| Caption | System sans | 12px | 400 |
| Micro | System sans | 11px | 400 |
| Code | System mono | 13px | 400 |

---

## 11. Spacing

| Context | Value |
|---------|-------|
| Page padding | 24px |
| Card padding | 14px-16px |
| Card gap | 10px-12px |
| Section margin | 16px-20px |
| Inline gap | 8px-10px |

---

## 12. Key Decisions

- 深色主题为唯一主题（不做日间模式切换，V0 不做）
- 不使用 Ant Design 默认蓝色 Token，全部覆盖为自定义配色
- 进度指示器用三步状态而非百分比进度条
- Data 预览用 ag-grid，不用 Ant Design Table
- 所有 ECharts 图表自动适配深色背景
