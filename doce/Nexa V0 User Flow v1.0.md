# Nexa V0 User Flow

Version: 1.0

---

# 1. Overall User Journey

用户进入 Nexa：

打开应用

↓

创建项目

↓

导入数据

↓

AI理解数据

↓

用户提出分析问题

↓

Nexa执行分析

↓

生成Insight

↓

保存分析结果

↓

继续探索数据


---

# 2. First Time User Flow（首次使用）


## Step 1: Open Nexa

用户打开 Nexa。


页面：

Welcome Page


展示：

"Nexa - Your AI Data Analyst"


主要入口：

[Create New Project]


---

## Step 2: Create Project


用户点击：

Create Project


输入：

Project Name


例如：

"Sales Analysis"


创建后进入项目空间。


---

## Step 3: Import Data


用户看到：

Data Import Page


选择：

Upload File

或者：

Connect Database


支持：

CSV

Excel

SQLite

MySQL


---

## Step 4: Data Understanding


数据上传后：

Nexa 自动分析：


- 文件大小

- 数据行数

- 字段数量

- 字段类型

- 缺失值

- 数据样例


展示：

"Your dataset is ready."


例如：


Dataset:

sales.csv


Rows:

120,000


Columns:

15


Detected:

sales_amount

date

region

product


---

# 3. Analysis Flow（核心流程）


## Step 5: User Ask Question


用户进入 Chat。


输入：

"分析最近一个月销售下降原因"


---

## Step 6: Nexa Understand


Nexa 返回：

理解结果。


例如：


"I will analyze:

1. Sales trend

2. Regional performance

3. Product performance"


用户确认：

[Start Analysis]


---

## Step 7: Data Analysis


Nexa执行：


理解意图

↓

分析规划

↓

数据查询

↓

统计分析

↓

生成图表


用户看到实时进度（SSE流式更新）：

```
🔄 Analyzing your data...

🧠 Understanding your question...       [Done ✓]
📋 Planning analysis steps...            [Done ✓]
⚡ Generating SQL query...               [Running...]
🔍 Executing query on 120,000 rows...    [Pending]
📊 Analyzing results...                  [Pending]
📈 Generating charts...                  [Pending]
💡 Generating insight...                 [Pending]
```

已完成阶段显示绿色勾选，当前阶段显示旋转动画，待执行阶段显示灰色。整个流程预计 30-60 秒，进度条持续更新。


---

## Step 8: Generate Insight


结果页面：


包含：


## Summary

销售下降15%


## Key Findings

主要来自：

华东地区

产品A


## Visualization

折线图

柱状图


## Recommendation

建议检查库存问题


---

# 4. Follow-up Exploration


用户继续：

"为什么华东下降最多？"


Nexa：

基于当前上下文继续分析。


不需要重新上传数据。



## Advanced: Open in Notebook

当 Chat 响应包含 SQL 或 Python 代码时，用户看到 [📓 Open in Notebook] 按钮：

用户点击 →

自动跳转到 Notebook 页面

Notebook 自动填充：

- Markdown 单元格：分析上下文说明
- SQL 单元格：AI 生成的查询
- Python 单元格：可视化代码

用户可以在 Notebook 中手动修改代码、调整参数、添加自定义分析，然后将结果保存回 Insight。


---

# 5. Save Result


用户点击：

Save Insight


保存：


- Question

- SQL

- Chart

- Analysis Result


形成：

Insight Card


---

# 6. Project Return Flow


以后进入项目：

看到：


Project Home


包含：

Dataset

Previous Questions

Insights

Charts


继续分析。

---

# 7. V0 Main User Loop


核心循环：


Data

↓

Question

↓

Analysis

↓

Insight

↓

New Question


这是 Nexa V0 最重要的体验。


---

# 8. V0 User Flow Principle


## Principle 1

用户描述目标。

不是操作工具。


错误：

"帮我生成SQL"


正确：

"分析退款率"


---

## Principle 2

分析过程透明。


用户应该看到：

AI正在做什么。


---

## Principle 3

每一次分析都是可复用资产。


保存：

问题

分析过程

结果


---

# End