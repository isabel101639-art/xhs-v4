#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整更新话题数据"""

import sys
sys.path.append('/root/xhs_v4')

from app import app, db, Topic, Activity

with app.app_context():
    Topic.query.delete()
    activity = Activity.query.first()
    
    # 完整数据 - 每个话题独立的信息
    topics_rugan = [
        {"topic_name": "肝硬化吃什么药？-产品实拍笔记类型", 
         "keywords": "带话题#肝硬化、#肝硬化治疗、#肝硬化调理、#肝硬化吃什么药、#肝硬化护理、#肝硬化怎么办\n#抗纤维化药物 #中成药调理#肝病用药#肝病日常 #养肝用药#肝硬化吃什么药\n#我的药盒 #遵医嘱（其他话题可以根据具体内容带）", 
         "direction": "产品实拍+复查报告\n1.人设是患者，内容要符合人设，描述自身经历贴合肝硬化症状同类人群的痛点，内容要像生活碎片，而非药品说明书。\n2.封面图是产品实拍图+复查报告or晒两次FibroScan报告对比，其他图按照笔记内容配合适的\n3.标题内文不要写产品名鳖甲软肝片，封面图已经有了，避免被小红书限流。\n4.报告关键信息打码：姓名、医院名称、病历号必须抹掉。数值清晰，要让人看清具体数值（如FibroScan 16.8）。可以圈出，用红圈把下降的数值圈出来，一目了然。日期可见，保留报告日期，证明时间跨度\n5.评论区维护，如果3天内没有真实用户留评，找个小红书账号评论。然后回复里面带\"软肝片\"。",
         "writing_example": "【封面】产品实拍图+复查报告对比图\n【内容】患者自述治疗经历\n【互动】评论区引导讨论",
         "reference_link": "https://www.xiaohongshu.com/explore/6888678f0000000003030ad6\nhttp://xhslink.com/o/8cyydyxkm2r\nhttp://xhslink.com/o/VjD9USMMmQ\nhttp://xhslink.com/o/6xuxao0eRUS\nhttps://www.xiaohongshu.com/explore/697a723600000000280230d6\nhttps://www.xiaohongshu.com/discovery/item/6861e397000000000d0188c8\nhttps://www.xiaohongshu.com/discovery/item/6203b2b300000000010244f1\nhttps://www.xiaohongshu.com/discovery/item/65f1cfce0000000012030880\nhttps://www.xiaohongshu.com/discovery/item/6739bbac000000003c019b25\nhttps://www.xiaohongshu.com/discovery/item/6810bcb3000000002100cca8\nhttps://www.xiaohongshu.com/discovery/item/67daf891000000000b0178ea",
         "quota": 6, "group_num": "第一组"},
         
        {"topic_name": "肝硬化吃什么药？-产品+其他并发症药物合集实拍", 
         "keywords": "带话题#肝硬化、#肝硬化治疗、#肝硬化调理、#肝硬化吃什么药、#肝硬化护理、#肝硬化怎么办\n#抗纤维化药物 #中成药调理#肝病用药#肝病日常 #养肝用药#肝硬化吃什么药\n#我的药盒 #遵医嘱", 
         "direction": "1.图片：产品+其他并发症药物合集实拍\n2.标题内文不要写产品名鳖甲软肝片，可写\"软肝片\"，不写用代指最佳，封面图已经有了，避免被小红书限流。\n3.评论区维护，如果3天内没有真实用户留评，找个小红书账号评论。然后回复里面带\"软肝片\"。",
         "writing_example": "【封面】多药品合集实拍\n【内容】分享多种保肝药品使用体验\n【互动】评论区交流药品选择",
         "reference_link": "https://www.xiaohongshu.com/discovery/item/6803b04a0000000007036d25\nhttps://www.xiaohongshu.com/discovery/item/68aff0ed000000001d03acc0\nhttps://www.xiaohongshu.com/discovery/item/668b31ae000000000a006ecb\nhttps://www.xiaohongshu.com/discovery/item/66226efd000000000103001d\nhttp://xhslink.com/o/7jPls6m7xnb",
         "quota": 6, "group_num": "第一组"},

        {"topic_name": "肝硬化吃什么药？-大字报封面图互动型", 
         "keywords": "带话题#肝硬化、#肝硬化治疗、#肝硬化调理、#肝硬化吃什么药、#肝硬化护理、#肝硬化怎么办\n#抗纤维化药物 #中成药调理#肝病用药#肝病日常 #养肝用药#肝硬化吃什么药\n#我的药盒 #遵医嘱", 
         "direction": "1.这种类型的笔记，重在引起用户的共鸣和评论区留言互动，\n以患者或患者家属身份分享经验或在小红书询问肝硬化护理调理治疗经验（吸引同类讨论）\n2.封面图、标题内文不要写产品名，选准用户痛点吸引患者/家属参与讨论\n3.引流为主，内容要避免被小红书限流。\n4.评论区维护互动，如果3天内没有真实用户留评，找个小红书账号评论。然后回复里面带\"鳖甲软肝片\"。",
         "writing_example": "【封面】大字报痛点问题\n【内容】引发共鸣的肝硬化困扰分享\n【互动】评论区热闹，积极回复",
         "reference_link": "https://www.xiaohongshu.com/explore/69956952000000000a029bf4\nhttps://www.xiaohongshu.com/explore/6890b14d00000000250226ec\nhttps://www.xiaohongshu.com/explore/6804d8f0000000001a0047f3\nhttp://xhslink.com/o/8QTDNXayxK3\nhttp://xhslink.com/o/3cMMt37RKaM\nhttp://xhslink.com/o/5oQW38jLob1\nhttp://xhslink.com/o/9m8P901U1HL",
         "quota": 6, "group_num": "第一组"},

        {"topic_name": "肝硬化吃什么药？-用医疗行业背景深度科普", 
         "keywords": "带话题#肝硬化、#肝硬化治疗、#肝硬化调理、#肝硬化吃什么药、#肝硬化护理、#肝硬化怎么办\n#抗纤维化药物 #中成药调理#肝病用药#肝病日常 #养肝用药#肝硬化吃什么药\n#我的药盒 #遵医嘱", 
         "direction": "1.用专业身份建立信任，用文献数据支撑观点，用科学逻辑解释原理。你将扮演医疗行业从业者（如医学编辑、临床研究协调员、药学背景等）、医学生、营养师等身份\n2.深度科普为主：如文献解读/研报解读/热点相关事件解读/行业资深观点/AI回复纠错等等。\n这种分享攻略笔记/专业知识科普/科研相关资料等等，图文表现形式不限，重点是内容必须有明确权威依据。\n3.可做产品成分配方解读笔记类型：很多患者既想尝试中药调理，又担心\"中药到底有没有用\"、\"会不会伤肝\"、\"是不是骗人的\"。用科学的态度、真实的经历、通俗的解释讲解鳖甲软肝片的成分配方，告诉用户：中药调理有用，但要讲究方法、讲究科学、讲究正规。\n3.截取文献提到鳖甲软肝片部分，有依据可带产品名。\n4.图片和内文产品名指代最佳，一定要带药品名称，带\"软肝片\"即可",
         "writing_example": "【封面】专业医学背景图\n【内容】文献解读+成分分析\n【互动】专业答疑",
         "reference_link": "https://www.xiaohongshu.com/explore/67b4999e0000000003028090\nhttps://www.xiaohongshu.com/explore/68de91500000000003021cdf\nhttps://www.xiaohongshu.com/explore/68b72292000000001b031148\nhttps://www.xiaohongshu.com/explore/67a5f684000000002901626c\nhttp://xhslink.com/o/3f9zLO529qm\nhttps://www.xiaohongshu.com/explore/69589219000000001d03c0d5\nhttps://www.xiaohongshu.com/explore/6149e4c2000000000102e78b\nhttp://xhslink.com/o/4EXk3MmPkun",
         "quota": 6, "group_num": "第二组"},

        {"topic_name": "肝硬化吃什么药？-横向测评笔记", 
         "keywords": "带话题#肝硬化、#肝硬化治疗、#肝硬化调理、#肝硬化吃什么药、#肝硬化护理、#肝硬化怎么办\n#抗纤维化药物 #中成药调理#肝病用药#肝病日常 #养肝用药#肝硬化吃什么药\n#我的药盒 #遵医嘱", 
         "direction": "1）纯竞品对比——多药对比型，吃过/了解过几种，客观对比\n以医疗背景，学习分享、个人经验的方式，科普肝硬化常用的中成药，讲清楚不同中成药的区别，让用户理解鳖甲软肝片为什么是其中一种选择，以及它适合什么样的情况。\n结合对其他药的了解，强调个人选择和医生建议，更多展示对多种药的了解，客观对比，不贬低其他，鳖甲软肝片放第1页或者合集图片放核心位置\n2）药品合集类型笔记内文可带\"鳖甲软肝片\"产品名\n3)这种类型的笔记只要能发布成功并被小红书收录即可，流量会受限，但是搜索流量比较稳定（测试的重点）",
         "writing_example": "【封面】多药品对比图\n【内容】客观对比各药品优缺点\n【互动】引导评论区讨论",
         "reference_link": "https://www.xiaohongshu.com/discovery/item/6982a33e000000000e03edb6\nhttps://www.xiaohongshu.com/discovery/item/66eac2670000000012013f58\nhttps://www.xiaohongshu.com/discovery/item/6916fd06000000000700b3ef\nhttps://www.xiaohongshu.com/discovery/item/68d3af560000000011015c3f\nhttps://www.xiaohongshu.com/discovery/item/68e8d9780000000007002dfe\nhttps://www.xiaohongshu.com/discovery/item/695731d0000000002102bb04\nhttps://www.xiaohongshu.com/discovery/item/66d6b27c000000001d01776f\nhttps://www.xiaohongshu.com/discovery/item/693bde69000000001e014987",
         "quota": 6, "group_num": "第二组"},

        {"topic_name": "肝硬化吃什么药？-备忘录图表攻略笔记", 
         "keywords": "带话题#肝硬化、#肝硬化治疗、#肝硬化调理、#肝硬化吃什么药、#肝硬化护理、#肝硬化怎么办\n#抗纤维化药物 #中成药调理#肝病用药#肝病日常 #养肝用药#肝硬化吃什么药\n#我的药盒 #遵医嘱", 
         "direction": "1.做\"信息的整理者\"，不做\"卖药的\"，当用户搜\"吃什么药\"时，她其实想搜的是\"别人/医生都开了什么药？我该吃什么药？哪些药是必须吃的？\"你的角色应该是：\"久病成医的患者/细心的家属/爱整理笔记的医学生\"，将复杂的用药逻辑整理成清晰的图表。\n2.这类笔记的核心是 \"科普分类 + 展现标准治疗方案\"。通过清晰的图表，让用户自己得出结论：\"哦，原来除了抗病毒的，还需要吃抗纤维化的中成药（比如软肝片）。\"",
         "writing_example": "【封面】备忘录风格图表\n【内容】用药分类图表+注意事项\n【互动】引导收藏转发",
         "reference_link": "http://xhslink.com/o/4XCMPijcYV6\nhttp://xhslink.com/o/AhBh2BtOPvq\nhttp://xhslink.com/o/AxQKE1zwDra\nhttp://xhslink.com/o/9UdwnBpUKof\nhttp://xhslink.com/o/u4XOK8VXDk\nhttp://xhslink.com/o/7Mja1XApWTa\nhttp://xhslink.com/o/suFeFXn6oj\nhttp://xhslink.com/o/8Z4S2Q97tPJ",
         "quota": 6, "group_num": "第二组"},
    ]

    # 添加剩余话题（简化版）
    remaining = [
        {"topic_name": "肝纤维化吃什么药？-产品实拍笔记类型", "keywords": "#肝纤维化是什么意思 #肝纤维化还能恢复吗 #肝纤维化四项指标 #肝纤维化到肝硬化多久 #肝纤维化 #肝纤维化怎么调理 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "撰写说明同上", "writing_example": "参考肝硬化产品实拍笔记类型", "reference_link": "http://xhslink.com/o/AJtR3J5kXoj\nhttp://xhslink.com/o/An55x9iiZ8y\nhttp://xhslink.com/o/439whvOvh9f\nhttp://xhslink.com/o/A3BFgPragXW\nhttp://xhslink.com/o/8ZofUud8nJD\nhttp://xhslink.com/o/uL89fkA7nY\nhttp://xhslink.com/o/2ldIorL2RFD", "quota": 6, "group_num": "第三组"},
        {"topic_name": "肝纤维化吃什么药？-产品+其他并发症药物合集实拍", "keywords": "#肝纤维化是什么意思 #肝纤维化还能恢复吗 #肝纤维化四项指标 #肝纤维化到肝硬化多久 #肝纤维化 #肝纤维化怎么调理 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "撰写说明同上", "writing_example": "参考肝硬化合集笔记类型", "reference_link": "https://www.xiaohongshu.com/discovery/item/6803b04a0000000007036d25\nhttps://www.xiaohongshu.com/discovery/item/68aff0ed000000001d03acc0\nhttps://www.xiaohongshu.com/discovery/item/668b31ae000000000a006ecb\nhttps://www.xiaohongshu.com/discovery/item/66226efd000000000103001d\nhttp://xhslink.com/o/7jPls6m7xnb", "quota": 6, "group_num": "第三组"},
        {"topic_name": "肝纤维化吃什么药？-大字报封面图互动型", "keywords": "#肝纤维化是什么意思 #肝纤维化还能恢复吗 #肝纤维化四项指标 #肝纤维化到肝硬化多久 #肝纤维化 #肝纤维化怎么调理 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "撰写说明同上", "writing_example": "参考肝硬化互动型", "reference_link": "https://www.xiaohongshu.com/explore/69956952000000000a029bf4\nhttps://www.xiaohongshu.com/explore/6890b14d00000000250226ec\nhttps://www.xiaohongshu.com/explore/6804d8f0000000001a0047f3\nhttp://xhslink.com/o/8QTDNXayxK3\nhttp://xhslink.com/o/3cMMt37RKaM\nhttp://xhslink.com/o/5oQW38jLob1\nhttp://xhslink.com/o/9m8P901U1HL", "quota": 6, "group_num": "第三组"},
        {"topic_name": "肝纤维化吃什么药？-用医疗行业背景深度科普", "keywords": "#肝纤维化是什么意思 #肝纤维化还能恢复吗 #肝纤维化四项指标 #肝纤维化到肝硬化多久 #肝纤维化 #肝纤维化怎么调理 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "撰写说明同上", "writing_example": "参考肝硬化科普型", "reference_link": "https://www.xiaohongshu.com/explore/67b4999e0000000003028090\nhttps://www.xiaohongshu.com/explore/68de91500000000003021cdf\nhttps://www.xiaohongshu.com/explore/68b72292000000001b031148", "quota": 6, "group_num": "第四组"},
        {"topic_name": "肝纤维化吃什么药？-横向测评笔记", "keywords": "#肝纤维化是什么意思 #肝纤维化还能恢复吗 #肝纤维化四项指标 #肝纤维化到肝硬化多久 #肝纤维化 #肝纤维化怎么调理 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "撰写说明同上", "writing_example": "参考肝硬化测评型", "reference_link": "https://www.xiaohongshu.com/discovery/item/6982a33e000000000e03edb6\nhttps://www.xiaohongshu.com/discovery/item/66eac2670000000012013f58\nhttps://www.xiaohongshu.com/discovery/item/6916fd06000000000700b3ef", "quota": 6, "group_num": "第四组"},
        {"topic_name": "肝纤维化吃什么药？-备忘录图表攻略笔记", "keywords": "#肝纤维化是什么意思 #肝纤维化还能恢复吗 #肝纤维化四项指标 #肝纤维化到肝硬化多久 #肝纤维化 #肝纤维化怎么调理 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "撰写说明同上", "writing_example": "参考肝硬化备忘录型", "reference_link": "http://xhslink.com/o/4XCMPijcYV6\nhttp://xhslink.com/o/AhBh2BtOPvq\nhttp://xhslink.com/o/AxQKE1zwDra", "quota": 6, "group_num": "第四组"},
        {"topic_name": "解酒护肝药物推荐-产品实拍笔记类型", "keywords": "#解酒护肝小妙招 #酒局必备 #肝细胞修复 #护肝好物 #解酒药推荐 #解酒 #解酒神器 #解酒护肝推荐 #护肝解酒药推荐 #长期喝酒的人怎么护肝", "direction": "撰写说明同上", "writing_example": "产品实拍+使用体验", "reference_link": "http://xhslink.com/o/5myw0y2RdgO\nhttp://xhslink.com/o/1HIfWlGflAE\nhttp://xhslink.com/o/4myw0y2RdgO", "quota": 6, "group_num": "第五组"},
        {"topic_name": "解酒护肝药物推荐-产品解酒好物合集实拍", "keywords": "#解酒护肝小妙招 #酒局必备 #肝细胞修复 #护肝好物 #解酒药推荐 #解酒 #解酒神器 #解酒护肝推荐 #护肝解酒药推荐 #长期喝酒的人怎么护肝", "direction": "撰写说明同上", "writing_example": "好物合集实拍", "reference_link": "http://xhslink.com/o/6fR3NZ7l5pv\nhttp://xhslink.com/o/3vpbFYZKTGO\nhttp://xhslink.com/o/7fR3NZ7l5pv", "quota": 6, "group_num": "第五组"},
        {"topic_name": "解酒护肝药物推荐-大字报封面图互动型", "keywords": "#解酒护肝小妙招 #酒局必备 #肝细胞修复 #护肝好物 #解酒药推荐 #解酒 #解酒神器 #解酒护肝推荐 #护肝解酒药推荐 #长期喝酒的人怎么护肝", "direction": "撰写说明同上", "writing_example": "大字报互动型", "reference_link": "http://xhslink.com/o/3kBPFXBtIy4\nhttp://xhslink.com/o/cngxDYZKTGO", "quota": 6, "group_num": "第五组"},
        {"topic_name": "解酒护肝药物推荐-用医疗行业背景深度科普", "keywords": "#解酒护肝小妙招 #酒局必备 #肝细胞修复 #护肝好物 #解酒药推荐 #解酒 #解酒神器 #解酒护肝推荐 #护肝解酒药推荐 #长期喝酒的人怎么护肝", "direction": "撰写说明同上", "writing_example": "医疗科普型", "reference_link": "http://xhslink.com/o/2z5EksxROE2\nhttp://xhslink.com/o/3QUl1g0BG10", "quota": 6, "group_num": "第六组"},
        {"topic_name": "解酒护肝药物推荐-横向测评笔记", "keywords": "#解酒护肝小妙招 #酒局必备 #肝细胞修复 #护肝好物 #解酒药推荐 #解酒 #解酒神器 #解酒护肝推荐 #护肝解酒药推荐 #长期喝酒的人怎么护肝", "direction": "撰写说明同上", "writing_example": "横向测评", "reference_link": "http://xhslink.com/o/AcjRmRgJUEm\nhttp://xhslink.com/o/AbV6CvYagoe", "quota": 6, "group_num": "第六组"},
        {"topic_name": "解酒护肝药物推荐-备忘录图表攻略笔记", "keywords": "#解酒护肝小妙招 #酒局必备 #肝细胞修复 #护肝好物 #解酒药推荐 #解酒 #解酒神器 #解酒护肝推荐 #护肝解酒药推荐 #长期喝酒的人怎么护肝", "direction": "撰写说明同上", "writing_example": "备忘录攻略", "reference_link": "http://xhslink.com/o/81Q4S43djJ5\nhttp://xhslink.com/o/7bQON3JyvdR", "quota": 6, "group_num": "第六组"},
    ]
    
    # FibroScan话题
    topics_fibro = [
        {"topic_name": "父母体检套餐怎么选", "keywords": "父母体检套餐选择", "direction": "为父母选择合适的体检套餐", "writing_example": "分享选择体检套餐的经验", "reference_link": "", "quota": 10, "group_num": "第七组"},
        {"topic_name": "父母体检必做项目", "keywords": "父母体检必做项目", "direction": "父母体检必做项目推荐", "writing_example": "必做体检项目清单", "reference_link": "", "quota": 10, "group_num": "第七组"},
        {"topic_name": "带父母体检做什么项目", "keywords": "带父母体检项目", "direction": "带父母体检项目推荐", "writing_example": "体检项目推荐", "reference_link": "", "quota": 10, "group_num": "第八组"},
        {"topic_name": "爸妈体检项目怎么选", "keywords": "爸妈体检项目选择", "direction": "爸妈体检项目选择建议", "writing_example": "选择建议", "reference_link": "", "quota": 10, "group_num": "第八组"},
        {"topic_name": "老年人体检必检项目", "keywords": "老年人体检项目", "direction": "老年人体检必检项目", "writing_example": "必检项目", "reference_link": "", "quota": 10, "group_num": "第八组"},
    ]
    
    # 添加所有话题
    for t in topics_rugan:
        topic = Topic(activity_id=activity.id, **t)
        db.session.add(topic)
    
    for t in remaining:
        topic = Topic(activity_id=activity.id, **t)
        db.session.add(topic)
    
    for t in topics_fibro:
        topic = Topic(activity_id=activity.id, **t)
        db.session.add(topic)
    
    db.session.commit()
    print(f"已添加所有话题")
