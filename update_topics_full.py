#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整更新话题数据"""

import sys
sys.path.append('/root/xhs_v4')

from app import app, db, Topic, Activity

with app.app_context():
    Topic.query.delete()
    activity = Activity.query.first()
    
    # 复方鳖甲软肝片话题 (18个)
    topics_rugan = [
        {"topic_name": "肝硬化吃什么药？-产品实拍笔记类型", "keywords": "#肝硬化 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "产品实拍+复查报告\n1.人设是患者，内容要符合人设，描述自身经历贴合肝硬化症状同类人群的痛点，内容要像生活碎片，而非药品说明书。\n2.封面图是产品实拍图+复查报告or晒两次FibroScan报告对比。\n3.标题内文不要写产品名鳖甲软肝片，封面图已经有了，避免被小红书限流。\n4.报告关键信息打码：姓名、医院名称、病历号必须抹掉。数值清晰，要让人看清具体数值。\n5.评论区维护，如果3天内没有真实用户留评，找个小红书账号评论。然后回复里面带“软肝片”。", "reference_link": "https://www.xiaohongshu.com/explore/6888678f0000000003030ad6", "quota": 6, "group_num": "第一组"},
        {"topic_name": "肝硬化吃什么药？-产品+其他并发症药物合集实拍", "keywords": "#肝硬化 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "产品+其他并发症药物合集实拍\n1.图片：产品+其他并发症药物合集实拍\n2.标题内文不要写产品名鳖甲软肝片，可写”软肝片“，不写用代指最佳。\n3.评论区维护，如果3天内没有真实用户留评，找个小红书账号评论。然后回复里面带“软肝片”。", "reference_link": "https://www.xiaohongshu.com/discovery/item/6803b04a0000000007036d25", "quota": 6, "group_num": "第一组"},
        {"topic_name": "肝硬化吃什么药？-大字报封面图互动型", "keywords": "#肝硬化 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "大字报封面图互动型\n1.这种类型的笔记，重在引起用户的共鸣和评论区留言互动。\n2.以患者或患者家属身份分享经验或在小红书询问肝硬化护理调理治疗经验（吸引同类讨论）\n3.封面图、标题内文不要写产品名，选准用户痛点吸引患者/家属参与讨论。\n4.引流为主，内容要避免被小红书限流。\n5.评论区维护互动，如果3天内没有真实用户留评，找个小红书账号评论。然后回复里面带“鳖甲软肝片”。", "reference_link": "https://www.xiaohongshu.com/explore/69956952000000000a029bf4", "quota": 6, "group_num": "第一组"},
        {"topic_name": "肝硬化吃什么药？-用医疗行业背景深度科普", "keywords": "#肝硬化 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "医疗行业背景深度科普\n1.用专业身份建立信任，用文献数据支撑观点，用科学逻辑解释原理。\n2.深度科普为主：如文献解读/研报解读/热点相关事件解读/行业资深观点/AI回复纠错等等。\n3.可做产品成分配方解读笔记类型：用科学的态度、真实的经历、通俗的解释讲解鳖甲软肝片的成分配方。\n4.截取文献提到鳖甲软肝片部分，有依据可带产品名。", "reference_link": "https://www.xiaohongshu.com/explore/67b4999e0000000003028090", "quota": 6, "group_num": "第二组"},
        {"topic_name": "肝硬化吃什么药？-横向测评笔记", "keywords": "#肝硬化 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "横向测评笔记\n1）纯竞品对比——多药对比型，吃过/了解过几种，客观对比。\n2）药品合集类型笔记内文可带”鳖甲软肝片“产品名。\n3)这种类型的笔记只要能发布成功并被小红书收录即可，流量会受限，但是搜索流量比较稳定。", "reference_link": "https://www.xiaohongshu.com/discovery/item/6982a33e000000000e03edb6", "quota": 6, "group_num": "第二组"},
        {"topic_name": "肝硬化吃什么药？-备忘录图表攻略笔记", "keywords": "#肝硬化 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "备忘录图表攻略笔记\n1.做“信息的整理者”，不做“卖药的”。\n2.将药物分为几大类：第一类（病因药）、第二类（抗纤药）、第三类（并发症/辅助）。\n3.通过这种分类排位，让用户潜意识里觉得“抗病毒+抗纤维化（软肝片）”是标准搭配。", "reference_link": "http://xhslink.com/o/4XCMPijcYV6", "quota": 6, "group_num": "第二组"},
        {"topic_name": "肝纤维化吃什么药？-产品实拍笔记类型", "keywords": "#肝纤维化是什么意思 #肝纤维化还能恢复吗 #肝纤维化四项指标 #肝纤维化到肝硬化多久 #肝纤维化 #肝纤维化怎么调理 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "产品实拍笔记类型（撰写说明同上）", "reference_link": "http://xhslink.com/o/AJtR3J5kXoj", "quota": 6, "group_num": "第三组"},
        {"topic_name": "肝纤维化吃什么药？-产品+其他并发症药物合集实拍", "keywords": "#肝纤维化是什么意思 #肝纤维化还能恢复吗 #肝纤维化四项指标 #肝纤维化到肝硬化多久 #肝纤维化 #肝纤维化怎么调理 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "产品+其他并发症药物合集实拍（撰写说明同上）", "reference_link": "https://www.xiaohongshu.com/discovery/item/6803b04a0000000007036d25", "quota": 6, "group_num": "第三组"},
        {"topic_name": "肝纤维化吃什么药？-大字报封面图互动型", "keywords": "#肝纤维化是什么意思 #肝纤维化还能恢复吗 #肝纤维化四项指标 #肝纤维化到肝硬化多久 #肝纤维化 #肝纤维化怎么调理 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "大字报封面图互动型（撰写说明同上）", "reference_link": "https://www.xiaohongshu.com/explore/69956952000000000a029bf4", "quota": 6, "group_num": "第三组"},
        {"topic_name": "肝纤维化吃什么药？-用医疗行业背景深度科普", "keywords": "#肝纤维化是什么意思 #肝纤维化还能恢复吗 #肝纤维化四项指标 #肝纤维化到肝硬化多久 #肝纤维化 #肝纤维化怎么调理 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "用医疗行业背景深度科普（撰写说明同上）", "reference_link": "https://www.xiaohongshu.com/explore/67b4999e0000000003028090", "quota": 6, "group_num": "第四组"},
        {"topic_name": "肝纤维化吃什么药？-横向测评笔记", "keywords": "#肝纤维化是什么意思 #肝纤维化还能恢复吗 #肝纤维化四项指标 #肝纤维化到肝硬化多久 #肝纤维化 #肝纤维化怎么调理 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "横向测评笔记（撰写说明同上）", "reference_link": "https://www.xiaohongshu.com/discovery/item/6982a33e000000000e03edb6", "quota": 6, "group_num": "第四组"},
        {"topic_name": "肝纤维化吃什么药？-备忘录图表攻略笔记", "keywords": "#肝纤维化是什么意思 #肝纤维化还能恢复吗 #肝纤维化四项指标 #肝纤维化到肝硬化多久 #肝纤维化 #肝纤维化怎么调理 #肝硬化治疗 #肝硬化调理 #肝硬化吃什么药 #肝硬化护理 #肝硬化怎么办 #抗纤维化药物 #中成药调理 #肝病用药 #肝病日常 #养肝用药 #我的药盒 #遵医嘱", "direction": "备忘录图表攻略笔记（撰写说明同上）", "reference_link": "http://xhslink.com/o/4XCMPijcYV6", "quota": 6, "group_num": "第四组"},
        {"topic_name": "解酒护肝药物推荐-产品实拍笔记类型", "keywords": "#解酒护肝小妙招 #酒局必备 #肝细胞修复 #护肝好物 #解酒药推荐 #解酒 #解酒神器 #解酒护肝推荐 #护肝解酒药推荐 #长期喝酒的人怎么护肝", "direction": "产品实拍笔记类型（撰写说明同上）", "reference_link": "http://xhslink.com/o/5myw0y2RdgO", "quota": 6, "group_num": "第五组"},
        {"topic_name": "解酒护肝药物推荐-产品解酒好物合集实拍", "keywords": "#解酒护肝小妙招 #酒局必备 #肝细胞修复 #护肝好物 #解酒药推荐 #解酒 #解酒神器 #解酒护肝推荐 #护肝解酒药推荐 #长期喝酒的人怎么护肝", "direction": "产品解酒好物合集实拍（撰写说明同上）", "reference_link": "http://xhslink.com/o/6fR3NZ7l5pv", "quota": 6, "group_num": "第五组"},
        {"topic_name": "解酒护肝药物推荐-大字报封面图互动型", "keywords": "#解酒护肝小妙招 #酒局必备 #肝细胞修复 #护肝好物 #解酒药推荐 #解酒 #解酒神器 #解酒护肝推荐 #护肝解酒药推荐 #长期喝酒的人怎么护肝", "direction": "大字报封面图互动型（撰写说明同上）", "reference_link": "http://xhslink.com/o/3kBPFXBtIy4", "quota": 6, "group_num": "第五组"},
        {"topic_name": "解酒护肝药物推荐-用医疗行业背景深度科普", "keywords": "#解酒护肝小妙招 #酒局必备 #肝细胞修复 #护肝好物 #解酒药推荐 #解酒 #解酒神器 #解酒护肝推荐 #护肝解酒药推荐 #长期喝酒的人怎么护肝", "direction": "用医疗行业背景深度科普（撰写说明同上）", "reference_link": "http://xhslink.com/o/2z5EksxROE2", "quota": 6, "group_num": "第六组"},
        {"topic_name": "解酒护肝药物推荐-横向测评笔记", "keywords": "#解酒护肝小妙招 #酒局必备 #肝细胞修复 #护肝好物 #解酒药推荐 #解酒 #解酒神器 #解酒护肝推荐 #护肝解酒药推荐 #长期喝酒的人怎么护肝", "direction": "横向测评笔记（撰写说明同上）", "reference_link": "http://xhslink.com/o/AcjRmRgJUEm", "quota": 6, "group_num": "第六组"},
        {"topic_name": "解酒护肝药物推荐-备忘录图表攻略笔记", "keywords": "#解酒护肝小妙招 #酒局必备 #肝细胞修复 #护肝好物 #解酒药推荐 #解酒 #解酒神器 #解酒护肝推荐 #护肝解酒药推荐 #长期喝酒的人怎么护肝", "direction": "备忘录图表攻略笔记（撰写说明同上）", "reference_link": "http://xhslink.com/o/81Q4S43djJ5", "quota": 6, "group_num": "第六组"},
    ]
    
    # FibroScan话题 (5个)
    topics_fibro = [
        {"topic_name": "父母体检套餐怎么选", "keywords": "父母体检套餐选择", "direction": "为父母选择合适的体检套餐", "reference_link": "", "quota": 10, "group_num": "第七组"},
        {"topic_name": "父母体检必做项目", "keywords": "父母体检必做项目", "direction": "父母体检必做项目推荐", "reference_link": "", "quota": 10, "group_num": "第七组"},
        {"topic_name": "带父母体检做什么项目", "keywords": "带父母体检项目", "direction": "带父母体检项目推荐", "reference_link": "", "quota": 10, "group_num": "第八组"},
        {"topic_name": "爸妈体检项目怎么选", "keywords": "爸妈体检项目选择", "direction": "爸妈体检项目选择建议", "reference_link": "", "quota": 10, "group_num": "第八组"},
        {"topic_name": "老年人体检必检项目", "keywords": "老年人体检项目", "direction": "老年人体检必检项目", "reference_link": "", "quota": 10, "group_num": "第八组"},
    ]
    
    for t in topics_rugan:
        topic = Topic(activity_id=activity.id, **t)
        db.session.add(topic)
    
    for t in topics_fibro:
        topic = Topic(activity_id=activity.id, **t)
        db.session.add(topic)
    
    db.session.commit()
    print(f"已添加{len(topics_rugan)+len(topics_fibro)}个话题")
