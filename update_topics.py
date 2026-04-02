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
    
    topics = [
        # 复方鳖甲软肝片 18个
        {"topic_name": "复方鳖甲软肝片效果好吗", "keywords": "复方鳖甲软肝片,肝纤维化,逆转", "direction": "分享药品治疗效果", "quota": 20, "group_num": "第一组"},
        {"topic_name": "复方鳖甲软肝片疗程", "keywords": "复方鳖甲软肝片,疗程,服用时间", "direction": "科普用药周期", "quota": 20, "group_num": "第一组"},
        {"topic_name": "复方鳖甲软肝片副作用", "keywords": "复方鳖甲软肝片,副作用,注意事项", "direction": "客观分析安全性", "quota": 20, "group_num": "第一组"},
        {"topic_name": "复方鳖甲软肝片价格", "keywords": "复方鳖甲软肝片,价格,多少钱", "direction": "说明价格及购买渠道", "quota": 20, "group_num": "第二组"},
        {"topic_name": "复方鳖甲软肝片怎么吃", "keywords": "复方鳖甲软肝片,用法,用量", "direction": "指导正确服用方法", "quota": 20, "group_num": "第二组"},
        {"topic_name": "肝纤维化能治好吗", "keywords": "肝纤维化,治疗,逆转", "direction": "科普肝纤维化知识", "quota": 20, "group_num": "第二组"},
        {"topic_name": "肝硬化吃什么药好", "keywords": "肝硬化,用药,治疗", "direction": "推荐治疗方案", "quota": 20, "group_num": "第三组"},
        {"topic_name": "护肝片哪个牌子好", "keywords": "护肝片,品牌,推荐", "direction": "对比各品牌护肝片", "quota": 20, "group_num": "第三组"},
        {"topic_name": "酒精肝吃什么好", "keywords": "酒精肝,护肝,饮食", "direction": "分享养护方法", "quota": 20, "group_num": "第三组"},
        {"topic_name": "脂肪肝如何消除", "keywords": "脂肪肝,消除,治疗", "direction": "科普脂肪肝防治", "quota": 20, "group_num": "第四组"},
        {"topic_name": "肝脏不好有什么症状", "keywords": "肝脏,症状,信号", "direction": "提醒养肝信号", "quota": 20, "group_num": "第四组"},
        {"topic_name": "养肝护肝吃什么", "keywords": "养肝,护肝,食疗", "direction": "推荐养肝食物", "quota": 20, "group_num": "第四组"},
        {"topic_name": "肝不好怎么调理", "keywords": "肝不好,调理,方法", "direction": "分享调理经验", "quota": 20, "group_num": "第五组"},
        {"topic_name": "复方鳖甲软肝片功效", "keywords": "复方鳖甲软肝片,功效,作用", "direction": "科普药品功效", "quota": 20, "group_num": "第五组"},
        {"topic_name": "肝纤维化吃什么药", "keywords": "肝纤维化,用药,治疗", "direction": "推荐用药方案", "quota": 20, "group_num": "第五组"},
        {"topic_name": "乙肝肝纤维化", "keywords": "乙肝,肝纤维化,治疗", "direction": "分享治疗经历", "quota": 20, "group_num": "第六组"},
        {"topic_name": "肝硬化早期症状", "keywords": "肝硬化,症状,早期", "direction": "提醒早期信号", "quota": 20, "group_num": "第六组"},
        {"topic_name": "复方鳖甲软肝片真实评价", "keywords": "复方鳖甲软肝片,评价,口碑", "direction": "分享真实使用感受", "quota": 20, "group_num": "第六组"},
        # FibroScan福波看 5个
        {"topic_name": "FibroScan是什么检查", "keywords": "FibroScan,肝脏弹性,无创检查", "direction": "科普FibroScan检查", "quota": 20, "group_num": "第七组"},
        {"topic_name": "FibroScan检查多少钱", "keywords": "FibroScan,价格,费用", "direction": "说明检查费用", "quota": 20, "group_num": "第七组"},
        {"topic_name": "FibroScan痛苦吗", "keywords": "FibroScan,检查,感受", "direction": "分享检查体验", "quota": 20, "group_num": "第七组"},
        {"topic_name": "肝脏硬度正常值", "keywords": "肝脏硬度,正常值,范围", "direction": "科普正常指标", "quota": 20, "group_num": "第八组"},
        {"topic_name": "FibroScan和肝穿的区别", "keywords": "FibroScan,肝穿,对比", "direction": "对比两种检查方式", "quota": 20, "group_num": "第八组"},
    ]
    
    for t in topics:
        topic = Topic(activity_id=activity.id, **t)
        db.session.add(topic)
    
    db.session.commit()
    print(f"已添加{len(topics)}个话题")
