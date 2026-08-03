"""Built-in skills registered at application startup."""
from skills import skill_registry


def register_builtin_skills():
    """Register all built-in skills."""

    # 1. Data Summary
    skill_registry.register_runtime("data_summary", {
        "title": "数据概览",
        "description": "自动生成数据集的整体概览：行数、列数、缺失值、数值分布",
        "category": "statistics",
        "icon": "BarChartOutlined",
        "version": "1.0.0",
        "is_builtin": True,
        "definition": {
            "steps": [
                {
                    "type": "sql",
                    "prompt": "生成数据集的整体统计信息：总行数、每列的数据类型、缺失值数量和比例。对于数值列，计算最小值、最大值、平均值和中位数。"
                },
                {
                    "type": "visualize",
                    "chart": "bar"
                },
                {
                    "type": "insight",
                    "prompt": "总结数据概览：1) 数据集整体规模 2) 哪些列有较多缺失值需要关注 3) 数值列的分布特点 4) 建议下一步分析方向"
                }
            ]
        }
    })

    # 2. Correlation Analysis
    skill_registry.register_runtime("correlation_analysis", {
        "title": "相关性分析",
        "description": "分析数值列之间的相关性，找出最相关的字段对",
        "category": "statistics",
        "icon": "DotChartOutlined",
        "version": "1.0.0",
        "is_builtin": True,
        "definition": {
            "steps": [
                {
                    "type": "sql",
                    "prompt": "计算所有数值列的两两相关系数。提示：DuckDB 的 CORR(col1, col2) 只能用于两个列。你需要手动枚举数值列对。输出 TOP 10 最强的相关系数（无论正负），包含两个列名和相关系数值，按绝对值降序排列。"
                },
                {
                    "type": "visualize",
                    "chart": "bar"
                },
                {
                    "type": "insight",
                    "prompt": "分析相关性结果：1) 最强的正相关是什么？背后的业务逻辑 2) 是否有负相关？说明什么 3) 给出 2-3 条基于相关性的业务建议"
                }
            ]
        }
    })

    # 3. Top/Bottom Finder
    skill_registry.register_runtime("top_bottom_finder", {
        "title": "排行榜分析",
        "description": "找出任意指标的前 N 名和后 N 名",
        "category": "analysis",
        "icon": "TrophyOutlined",
        "version": "1.0.0",
        "is_builtin": True,
        "definition": {
            "steps": [
                {
                    "type": "sql",
                    "prompt": "找出数据集中最重要的数值指标（如 sales、profit 等）的前 10 名和后 10 名。按照该指标降序排列前 10，升序排列后 10。如果有多列数值，选择最有业务意义的那一列。"
                },
                {
                    "type": "visualize",
                    "chart": "bar"
                },
                {
                    "type": "insight",
                    "prompt": "分析排行结果：1) 第一名和第二名差距大吗？说明什么 2) 垫底的是否有共同特征 3) 给出优化建议"
                }
            ]
        }
    })

    # 4. Trend Analysis
    skill_registry.register_runtime("trend_analysis", {
        "title": "趋势分析",
        "description": "分析时间序列趋势，按时间维度聚合，识别上升/下降模式",
        "category": "forecast",
        "icon": "LineChartOutlined",
        "version": "1.0.0",
        "is_builtin": True,
        "definition": {
            "steps": [
                {
                    "type": "sql",
                    "prompt": "如果数据集中有日期/时间列，按月份或季度聚合最重要的数值指标（如销售额、利润等），展示随时间的变化趋势。使用 DATE_TRUNC 或类似函数做时间聚合。如果数据集不包含日期列，输出一条提示消息。"
                },
                {
                    "type": "visualize",
                    "chart": "line"
                },
                {
                    "type": "insight",
                    "prompt": "分析趋势：1) 整体趋势是上升还是下降 2) 是否有明显的季节性波动 3) 有没有异常峰值或低谷 4) 基于趋势的预测和建议"
                }
            ]
        }
    })
