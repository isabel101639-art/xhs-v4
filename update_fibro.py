#!/usr/bin/env python3
"""更新FibroScan话题数据"""
import sqlite3

db_path = 'xhs_system.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# FibroScan完整数据
fibro_updates = [
    ("父母体检套餐怎么选",
     "#父母体检#父母体检套餐怎么选#爸妈体检#体检必做项目清单#父母体检套餐怎么选#父母体检推荐#体检套餐#中老年体检#父母健康#体检项目#父母体检项目#带父母体检",
     "类型1：体检套餐项目-列备忘录清单类型-攻略\n注意：根据参考的配图模式，需要找含FS体检套餐的医院/体检中心拍现场图。",
     "【封面】备忘录清单图\n【内容】体检项目清单\n【互动】引导收藏",
     "https://www.xiaohongshu.com/explore/691ed912000000001f008485\nhttps://www.xiaohongshu.com/discovery/item/669f16080000000027012bb5\nhttps://www.xiaohongshu.com/explore/682142980000000023015cfa\nhttps://www.xiaohongshu.com/discovery/item/68bccb54000000001b036f9b\nhttps://www.xiaohongshu.com/discovery/item/660c1b4f0000000004018503"),
    
    ("父母体检必做项目",
     "#父母体检#父母体检必做项目#父母体检必做项目清单#父母体检必做项目#父母体检推荐#体检必做项目#中老年体检#父母健康#体检项目#父母体检项目#带父母体检",
     "类型2：医院or体检中心-真实场景类型\n注意：根据参考的配图模式，需要找含FS体检套餐的医院/体检中心拍现场图。",
     "【封面】医院场景图+体检单\n【内容】必做项目解读\n【互动】专业答疑",
     "https://www.xiaohongshu.com/discovery/item/669f16080000000027012bb5\nhttps://www.xiaohongshu.com/explore/691ed912000000001f008485\nhttps://www.xiaohongshu.com/explore/682142980000000023015cfa"),
    
    ("带父母体检做什么项目",
     "#父母体检#带父母体检做什么项目#爸妈体检#体检#体检必做项目清单#带父母体检做什么项目#父母体检推荐#中老年体检#父母健康#体检项目#带父母体检",
     "类型3：大字报封面图类型\n注意：封面图大字报文字要带父母体检，用问句会好一点或者肯定句。",
     "【封面】大字报标题文字\n【内容】体检项目攻略\n【互动】引导讨论",
     "https://www.xiaohongshu.com/explore/682142980000000023015cfa\nhttps://www.xiaohongshu.com/explore/691ed912000000001f008485"),
    
    ("爸妈体检项目怎么选",
     "#父母体检#爸妈体检#体检#体检必做项目清单#爸妈体检项目怎么选#父母体检推荐#中老年体检#父母健康#体检项目#父母体检项目#带父母体检",
     "类型4：体检科普类型-科普图表\n注意：每篇笔记标题要带爸妈体检，内文要带爸妈体检项目怎么选关键字；",
     "【封面】科普图表\n【内容】项目选择指南\n【互动】引导收藏",
     "https://www.xiaohongshu.com/discovery/item/68bccb54000000001b036f9b\nhttps://www.xiaohongshu.com/discovery/item/669f16080000000027012bb5"),
    
    ("老年人体检必检项目",
     "#父母体检#爸妈体检#体检#体检必做项目清单#老年人体检必检项目#父母体检推荐#中老年体检#父母健康#体检项目#老年人体检#退休父母体检",
     "类型5：用医学背景-真诚分享体检攻略\n如：医疗公司职员/医学生/医药研究员等等身份",
     "【封面】医护背景图\n【内容】体检项目科普\n【互动】专业答疑",
     "https://www.xiaohongshu.com/discovery/item/660c1b4f0000000004018503\nhttps://www.xiaohongshu.com/discovery/item/68bccb54000000001b036f9b\nhttps://www.xiaohongshu.com/explore/682142980000000023015cfa"),
]

for topic_name, keywords, direction, example, links in fibro_updates:
    cursor.execute("""UPDATE topic SET keywords = ?, direction = ?, writing_example = ?, reference_link = ? 
        WHERE topic_name LIKE ?""", 
        (keywords, direction, example, links, f"%{topic_name}%"))

conn.commit()
print(f"已更新 {cursor.rowcount} 条FibroScan话题")
conn.close()
