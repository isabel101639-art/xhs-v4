#!/usr/bin/env python3
"""从Excel导入最新数据"""
import sqlite3
import pandas as pd
import sys

# Read Excel
df_rugan = pd.read_excel('小红书任务发布.xlsx', sheet_name='复方鳖甲软肝片')
df_fibro = pd.read_excel('小红书任务发布.xlsx', sheet_name='FibroScan')

db_path = 'xhs_system.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 清空旧数据
cursor.execute("DELETE FROM registration")
cursor.execute("DELETE FROM topic")
cursor.execute("DELETE FROM activity")

# 创建新活动
cursor.execute("INSERT INTO activity (name, title, description, status) VALUES (?, ?, ?, ?)",
    ("第1期", "福瑞医科小红书任务第一期", "邀请员工参与小红书推广任务", "published"))
activity_id = cursor.lastrowid

# 读取复方鳖甲软肝片话题
for i, row in df_rugan.iterrows():
    if i == 0:
        continue
    topic_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
    if not topic_name or topic_name == 'nan':
        continue
    
    quota = int(row.iloc[1]) if pd.notna(row.iloc[1]) else 6
    keywords = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""
    direction = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""
    example_col = str(row.iloc[4]) if pd.notna(row.iloc[4]) else ""
    
    # 提取链接
    links = []
    for part in example_col.split():
        if 'http' in part:
            links.append(part.strip())
    reference_link = '\n'.join(links)
    
    # 撰写示例从方向中提取或生成
    writing_example = ""
    if '产品实拍' in topic_name:
        writing_example = "【封面】产品实拍图+复查报告对比图\n【内容】患者自述治疗经历\n【互动】评论区引导讨论"
    elif '合集实拍' in topic_name:
        writing_example = "【封面】多药品合集实拍\n【内容】分享多种保肝药品使用体验\n【互动】评论区交流"
    elif '大字报' in topic_name or '互动型' in topic_name:
        writing_example = "【封面】大字报痛点问题\n【内容】引发共鸣的困扰分享\n【互动】评论区热闹"
    elif '科普' in topic_name or '深度' in topic_name:
        writing_example = "【封面】专业医学背景图\n【内容】文献解读+成分分析\n【互动】专业答疑"
    elif '测评' in topic_name:
        writing_example = "【封面】多药品对比图\n【内容】客观对比各药品优缺点\n【互动】引导讨论"
    elif '备忘录' in topic_name or '攻略' in topic_name:
        writing_example = "【封面】备忘录风格图表\n【内容】用药分类图表+注意事项\n【互动】引导收藏"
    else:
        writing_example = "【封面】实拍图\n【内容】分享使用体验\n【互动】评论区交流"
    
    group_num = f"话题{i}"
    
    cursor.execute("""INSERT INTO topic (activity_id, topic_name, keywords, direction, writing_example, reference_link, quota, group_num, filled)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""", 
        (activity_id, topic_name, keywords, direction, writing_example, reference_link, quota, group_num))

# 读取FibroScan话题
for i, row in df_fibro.iterrows():
    if i == 0:
        continue
    topic_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
    if not topic_name or topic_name == 'nan':
        continue
    
    quota = int(row.iloc[1]) if pd.notna(row.iloc[1]) else 10
    keywords = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""
    direction = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""
    writing_example = str(row.iloc[4]) if pd.notna(row.iloc[4]) else "分享体检经验"
    
    group_num = f"话题{i + 18}"
    
    cursor.execute("""INSERT INTO topic (activity_id, topic_name, keywords, direction, writing_example, reference_link, quota, group_num, filled)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""", 
        (activity_id, topic_name, keywords, direction, writing_example, "", quota, group_num))

conn.commit()
print(f"已导入: {cursor.rowcount} 条话题")
conn.close()
