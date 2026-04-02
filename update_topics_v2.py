#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""更新话题数据"""

import sys
sys.path.append('/root/xhs_v4')

from app import app, db, Topic, Activity

with app.app_context():
    # 清空旧话题
    Topic.query.delete()
    
    activity = Activity.query.first()
    
    # 复方鳖甲软肝片话题 (18个) - 放上面
    topics_rugan = [
        {"topic_name": "肝硬化吃什么药？-产品实拍笔记类型", "keywords": "肝硬化,治疗,药物", "direction": "产品实拍+复查报告类型", "quota": 6, "group_num": "第一组"},
        {"topic_name": "肝硬化吃什么药？-产品+其他并发症药物合集实拍", "keywords": "肝硬化,药物,合集", "direction": "产品+其他药物合集实拍", "quota": 6, "group_num": "第一组"},
        {"topic_name": "肝硬化吃什么药？-大字报封面图互动型", "keywords": "肝硬化,互动,经验", "direction": "大字报封面互动型", "quota": 6, "group_num": "第一组"},
        {"topic_name": "肝硬化吃什么药？-用医疗行业背景深度科普", "keywords": "肝硬化,科普,医疗", "direction": "医疗行业深度科普", "quota": 6, "group_num": "第二组"},
        {"topic_name": "肝硬化吃什么药？-横向测评笔记", "keywords": "肝硬化,测评,对比", "direction": "横向测评对比", "quota": 6, "group_num": "第二组"},
        {"topic_name": "肝硬化吃什么药？-备忘录图表攻略笔记", "keywords": "肝硬化,攻略,备忘录", "direction": "备忘录图表攻略", "quota": 6, "group_num": "第二组"},
        {"topic_name": "肝纤维化吃什么药？-产品实拍笔记类型", "keywords": "肝纤维化,治疗,药物", "direction": "产品实拍笔记", "quota": 6, "group_num": "第三组"},
        {"topic_name": "肝纤维化吃什么药？-产品+其他并发症药物合集实拍", "keywords": "肝纤维化,药物,合集", "direction": "产品+药物合集", "quota": 6, "group_num": "第三组"},
        {"topic_name": "肝纤维化吃什么药？-大字报封面图互动型", "keywords": "肝纤维化,互动,经验", "direction": "大字报互动型", "quota": 6, "group_num": "第三组"},
        {"topic_name": "肝纤维化吃什么药？-用医疗行业背景深度科普", "keywords": "肝纤维化,科普,医疗", "direction": "医疗深度科普", "quota": 6, "group_num": "第四组"},
        {"topic_name": "肝纤维化吃什么药？-横向测评笔记", "keywords": "肝纤维化,测评,对比", "direction": "横向测评", "quota": 6, "group_num": "第四组"},
        {"topic_name": "肝纤维化吃什么药？-备忘录图表攻略笔记", "keywords": "肝纤维化,攻略,备忘录", "direction": "备忘录攻略", "quota": 6, "group_num": "第四组"},
        {"topic_name": "解酒护肝药物推荐-产品实拍笔记类型", "keywords": "解酒,护肝,药物", "direction": "产品实拍", "quota": 6, "group_num": "第五组"},
        {"topic_name": "解酒护肝药物推荐-产品解酒好物合集实拍", "keywords": "解酒,护肝,合集", "direction": "好物合集", "quota": 6, "group_num": "第五组"},
        {"topic_name": "解酒护肝药物推荐-大字报封面图互动型", "keywords": "解酒,护肝,互动", "direction": "大字报互动", "quota": 6, "group_num": "第五组"},
        {"topic_name": "解酒护肝药物推荐-用医疗行业背景深度科普", "keywords": "解酒,护肝,科普", "direction": "医疗科普", "quota": 6, "group_num": "第六组"},
        {"topic_name": "解酒护肝药物推荐-横向测评笔记", "keywords": "解酒,护肝,测评", "direction": "横向测评", "quota": 6, "group_num": "第六组"},
        {"topic_name": "解酒护肝药物推荐-备忘录图表攻略笔记", "keywords": "解酒,护肝,攻略", "direction": "备忘录攻略", "quota": 6, "group_num": "第六组"},
    ]
    
    # FibroScan话题 (5个) - 放下面
    topics_fibro = [
        {"topic_name": "父母体检套餐怎么选", "keywords": "父母,体检,套餐", "direction": "体检套餐选择", "quota": 8, "group_num": "第七组"},
        {"topic_name": "父母体检必做项目", "keywords": "父母,体检,项目", "direction": "必做体检项目", "quota": 8, "group_num": "第七组"},
        {"topic_name": "带父母体检做什么项目", "keywords": "体检,项目,父母", "direction": "体检项目推荐", "quota": 8, "group_num": "第八组"},
        {"topic_name": "爸妈体检项目怎么选", "keywords": "爸妈,体检,选择", "direction": "体检选择", "quota": 8, "group_num": "第八组"},
        {"topic_name": "老年人体检必检项目", "keywords": "老年人,体检,项目", "direction": "老年体检", "quota": 8, "group_num": "第八组"},
    ]
    
    # 先添加复方鳖甲软肝片话题
    for t in topics_rugan:
        topic = Topic(activity_id=activity.id, **t)
        db.session.add(topic)
    
    # 再添加FibroScan话题
    for t in topics_fibro:
        topic = Topic(activity_id=activity.id, **t)
        db.session.add(topic)
    
    db.session.commit()
    print(f"已添加{len(topics_rugan)+len(topics_fibro)}个话题")
