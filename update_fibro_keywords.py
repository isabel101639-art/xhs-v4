#!/usr/bin/env python3
import sqlite3

db_path = 'xhs_system.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 更新FibroScan话题的关键词
cursor.execute("""UPDATE topic SET keywords = keywords || ' #FibroScan #福波看' 
    WHERE topic_name LIKE '%体检%'""")

conn.commit()
print(f"Updated {cursor.rowcount} topics")
conn.close()
