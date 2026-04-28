import json
from uuid import uuid4

from flask import jsonify, render_template, request

from models import Activity, AssetGenerationTask, AssetLibrary, CorpusEntry, HotTopicEntry, LiverIpProfilePlan, Registration, Submission, Topic, TrendNote


LIVER_SCIENCE_PUBLIC_KEYWORDS = [
    '肝', '脂肪肝', '肝纤维化', '肝硬化', '乙肝', '丙肝',
    '转氨酶', '肝功能', 'FibroScan', '福波看', '肝弹', '肝病',
    '保肝', '护肝', '养肝', '肝气郁结', '肝郁', '中医', '肝火', '湿热',
    '熬夜', '睡眠', '情绪', '减脂', '饮食', '体重', '女性',
]

LIVER_SCIENCE_IP_LANES = [
    {
        'key': 'report_interpretation',
        'title': '检查解读线',
        'description': '体检异常、转氨酶、FibroScan、肝弹、B超、复查趋势这些都可以长期写。',
        'tags': ['体检异常提醒', '检查报告解读', 'FibroScan/肝弹', '复查对比'],
    },
    {
        'key': 'fatty_liver_management',
        'title': '脂肪肝管理线',
        'description': '减脂、饮食、运动、代谢管理是非常大的内容池，适合做长期陪伴型IP。',
        'tags': ['脂肪肝逆转', '减脂管理', '饮食调整', '运动习惯'],
    },
    {
        'key': 'liver_care_habits',
        'title': '保肝护肝习惯线',
        'description': '从熬夜、应酬、作息、饮酒、护肝习惯切入，更贴近日常生活。',
        'tags': ['熬夜护肝', '应酬后恢复', '作息管理', '日常养肝'],
    },
    {
        'key': 'tcm_conditioning',
        'title': '中医调理线',
        'description': '可以从中医视角解释养肝、肝气郁结、肝胆湿热、情志与肝等内容。',
        'tags': ['中医养肝', '肝气郁结', '肝胆湿热', '疏肝理气'],
    },
    {
        'key': 'emotion_mindbody',
        'title': '情绪身心线',
        'description': '焦虑、压力、失眠、情绪波动和肝健康关联，是很有共鸣的一条IP内容线。',
        'tags': ['情绪与肝', '焦虑失眠', '压力管理', '身心调理'],
    },
    {
        'key': 'family_care',
        'title': '家庭照护线',
        'description': '从父母体检、家属陪诊、慢病照护、家庭沟通切入，适合家属型和陪伴型账号。',
        'tags': ['父母体检', '家属陪伴', '陪诊照护', '家庭沟通'],
    },
    {
        'key': 'women_health',
        'title': '女性与细分人群线',
        'description': '女性养肝、中年人、职场久坐人群、应酬人群，都能做成细分人设。',
        'tags': ['女性养肝', '职场久坐', '中年体检', '细分人群'],
    },
    {
        'key': 'myth_busting',
        'title': '误区纠偏线',
        'description': '“别再这样护肝”“很多人把脂肪肝想简单了”这类内容很适合出爆款。',
        'tags': ['误区纠偏', '反常识', '避坑提醒', '问答答疑'],
    },
    {
        'key': 'diet_nutrition',
        'title': '饮食营养线',
        'description': '吃什么、怎么吃、哪些习惯更伤肝或护肝，是很适合做收藏型内容的方向。',
        'tags': ['吃什么', '饮食调整', '营养建议', '食谱思路'],
    },
    {
        'key': 'exercise_fitness',
        'title': '运动减脂线',
        'description': '从走路、力量训练、减脂节奏到恢复习惯，都可以变成长期更新栏目。',
        'tags': ['运动减脂', '训练重启', '体重管理', '习惯养成'],
    },
]

LIVER_SCIENCE_PERSONA_LANES = [
    {
        'key': 'patient',
        'title': '患者本人',
        'description': '适合写真实经历、复查心态、生活调整和长期管理，更容易做共鸣。',
        'styles': ['真实经历', '复盘避坑', '情绪波动', '长期坚持'],
    },
    {
        'key': 'family',
        'title': '家属/陪诊者',
        'description': '适合写带父母体检、家人护肝、陪诊观察、家庭沟通，更有陪伴感。',
        'styles': ['照护观察', '家庭沟通', '陪诊记录', '体检陪伴'],
    },
    {
        'key': 'medical',
        'title': '医学科普型',
        'description': '适合把概念、指标、误区、流程讲清楚，建立专业信任感。',
        'styles': ['概念解释', '检查解读', '误区纠偏', '问答答疑'],
    },
    {
        'key': 'tcm',
        'title': '中医调理型',
        'description': '适合从养肝、疏肝理气、情志调理等视角切入，建立差异化风格。',
        'styles': ['中医辨证', '养生调理', '情志与肝', '日常养护'],
    },
    {
        'key': 'nutrition',
        'title': '健管/营养型',
        'description': '适合写饮食结构、减脂策略、生活方式管理，长期更新空间很大。',
        'styles': ['饮食清单', '减脂计划', '生活管理', '可执行建议'],
    },
    {
        'key': 'fitness',
        'title': '运动减脂型',
        'description': '适合把减脂执行、运动恢复和体能重建写成长期栏目，节奏感很强。',
        'styles': ['运动减脂', '体能重建', '习惯打卡', '执行反馈'],
    },
    {
        'key': 'women',
        'title': '女性健康型',
        'description': '适合把女性养肝、经期、更年期、情绪和生活节律串成个人IP。',
        'styles': ['女性养肝', '节律管理', '自我照顾', '长期陪伴'],
    },
    {
        'key': 'office',
        'title': '细分人群博主',
        'description': '比如女性养肝、职场久坐、应酬人群、体检复盘博主，更容易形成个人标签。',
        'styles': ['人群专属建议', '场景化表达', '经验总结', '长期栏目化'],
    },
]

LIVER_IP_COLUMN_BLUEPRINTS = {
    'report_interpretation': {
        'title': '每周体检解读',
        'audience': '体检异常、复查人群、第一次看报告的人',
        'cadence': '每周 2-3 条',
        'personas': ['体检复盘博主', '医学科普型', '医生助理'],
    },
    'fatty_liver_management': {
        'title': '脂肪肝管理日记',
        'audience': '脂肪肝、减脂、代谢异常人群',
        'cadence': '每周 2 条',
        'personas': ['健管/营养型', '运动减脂教练', '患者本人'],
    },
    'liver_care_habits': {
        'title': '日常护肝习惯',
        'audience': '熬夜、应酬、久坐、压力大的人群',
        'cadence': '每周 2 条',
        'personas': ['职场久坐人群', '健管/营养型', '患者本人'],
    },
    'tcm_conditioning': {
        'title': '中医调理养肝',
        'audience': '关注中医调理、肝气郁结、情志养肝的人群',
        'cadence': '每周 1-2 条',
        'personas': ['中医调理型', '女性健康视角', '情绪陪伴者'],
    },
    'emotion_mindbody': {
        'title': '情绪与肝',
        'audience': '焦虑、失眠、压力大、想做身心调理的人群',
        'cadence': '每周 1-2 条',
        'personas': ['情绪陪伴者', '患者本人', '中医调理型'],
    },
    'family_care': {
        'title': '父母体检与家庭照护',
        'audience': '家属、陪诊者、中年子女',
        'cadence': '每周 1 条',
        'personas': ['家属/陪诊者', '陪诊照护者', '细分人群博主'],
    },
    'women_health': {
        'title': '女性养肝栏目',
        'audience': '女性健康、自我照顾、生活节律人群',
        'cadence': '每周 1 条',
        'personas': ['女性健康视角', '中医调理型', '细分人群博主'],
    },
    'myth_busting': {
        'title': '护肝误区纠偏',
        'audience': '容易被网络碎片信息误导的人群',
        'cadence': '每周 1-2 条',
        'personas': ['医学科普型', '体检复盘博主', '医生助理'],
    },
    'diet_nutrition': {
        'title': '饮食营养怎么做',
        'audience': '想从日常饮食改善肝健康的人群',
        'cadence': '每周 1-2 条',
        'personas': ['健管/营养型', '女性健康视角', '患者本人'],
    },
    'exercise_fitness': {
        'title': '运动减脂怎么起步',
        'audience': '脂肪肝、久坐、减脂重启人群',
        'cadence': '每周 1 条',
        'personas': ['运动减脂教练', '职场久坐人群', '脂肪肝管理型'],
    },
}

LIVER_IP_GOAL_OPTIONS = {
    'trust': '建立专业信任',
    'growth': '涨粉和破圈',
    'consistency': '稳定更新不焦虑',
    'consulting': '沉淀咨询和沟通能力',
}

LIVER_IP_BACKGROUND_OPTIONS = {
    'patient': '患者本人',
    'family': '家属/陪诊者',
    'medical': '医学科普型',
    'tcm': '中医调理型',
    'nutrition': '健管/营养型',
    'fitness': '运动减脂教练',
    'women': '女性健康视角',
    'office': '职场久坐人群',
}

LIVER_IP_DIRECTION_OPTIONS = {
    'auto': '系统自动匹配',
    'report_interpretation': '检查解读线',
    'fatty_liver_management': '脂肪肝管理线',
    'liver_care_habits': '保肝护肝习惯线',
    'tcm_conditioning': '中医调理线',
    'emotion_mindbody': '情绪与肝线',
    'diet_nutrition': '饮食营养线',
    'exercise_fitness': '运动减脂线',
    'family_care': '家庭照护线',
    'women_health': '女性养肝线',
    'myth_busting': '误区纠偏线',
}

LIVER_IP_LANE_RELATIONS = {
    'report_interpretation': ['myth_busting', 'family_care', 'liver_care_habits'],
    'fatty_liver_management': ['diet_nutrition', 'exercise_fitness', 'emotion_mindbody'],
    'liver_care_habits': ['emotion_mindbody', 'diet_nutrition', 'exercise_fitness'],
    'tcm_conditioning': ['emotion_mindbody', 'women_health', 'liver_care_habits'],
    'emotion_mindbody': ['tcm_conditioning', 'liver_care_habits', 'women_health'],
    'family_care': ['report_interpretation', 'women_health', 'emotion_mindbody'],
    'women_health': ['tcm_conditioning', 'emotion_mindbody', 'diet_nutrition'],
    'myth_busting': ['report_interpretation', 'fatty_liver_management', 'liver_care_habits'],
    'diet_nutrition': ['fatty_liver_management', 'exercise_fitness', 'liver_care_habits'],
    'exercise_fitness': ['fatty_liver_management', 'diet_nutrition', 'emotion_mindbody'],
}

LIVER_IP_BACKGROUND_TO_PERSONA_KEY = {
    'patient': 'patient_self',
    'family': 'patient_family',
    'medical': 'medical_science',
    'tcm': 'tcm_practitioner',
    'nutrition': 'nutritionist',
    'fitness': 'fitness_coach',
    'women': 'women_health',
    'office': 'office_worker',
}

LIVER_IP_LANE_TO_SCENE_KEY = {
    'report_interpretation': 'report_interpretation',
    'fatty_liver_management': 'fatty_liver_management',
    'liver_care_habits': 'daily_liver_care',
    'tcm_conditioning': 'tcm_conditioning',
    'emotion_mindbody': 'mood_stress',
    'diet_nutrition': 'diet_adjustment',
    'exercise_fitness': 'exercise_rebuild',
    'family_care': 'family_support',
    'women_health': 'women_dailycare',
    'myth_busting': 'clinic_consulting',
}

LIVER_IP_LANE_TO_COPY_SKILL = {
    'report_interpretation': 'report_interpretation',
    'fatty_liver_management': 'practical_checklist',
    'liver_care_habits': 'story_empathy',
    'tcm_conditioning': 'story_empathy',
    'emotion_mindbody': 'story_empathy',
    'diet_nutrition': 'practical_checklist',
    'exercise_fitness': 'practical_checklist',
    'family_care': 'story_empathy',
    'women_health': 'story_empathy',
    'myth_busting': 'myth_busting',
}

LIVER_IP_LANE_TO_TITLE_SKILL = {
    'report_interpretation': 'checklist_collect',
    'fatty_liver_management': 'checklist_collect',
    'liver_care_habits': 'result_first',
    'tcm_conditioning': 'emotional_diary',
    'emotion_mindbody': 'emotional_diary',
    'diet_nutrition': 'checklist_collect',
    'exercise_fitness': 'checklist_collect',
    'family_care': 'emotional_diary',
    'women_health': 'emotional_diary',
    'myth_busting': 'conflict_reverse',
}

LIVER_IP_LANE_TO_IMAGE_SKILL = {
    'report_interpretation': 'report_decode',
    'fatty_liver_management': 'save_worthy_cards',
    'liver_care_habits': 'high_click_cover',
    'tcm_conditioning': 'story_atmosphere',
    'emotion_mindbody': 'story_atmosphere',
    'diet_nutrition': 'save_worthy_cards',
    'exercise_fitness': 'save_worthy_cards',
    'family_care': 'story_atmosphere',
    'women_health': 'story_atmosphere',
    'myth_busting': 'high_click_cover',
}


def register_public_routes(app, helpers):
    build_public_shell_context = helpers['build_public_shell_context']
    build_registration_tracking_summary = helpers['build_registration_tracking_summary']
    serialize_topic = helpers['serialize_topic']
    serialize_announcement = helpers['serialize_announcement']
    list_announcements = helpers['list_announcements']
    serialize_site_page_config = helpers['serialize_site_page_config']
    serialize_site_theme = helpers['serialize_site_theme']
    get_site_page_config = helpers['get_site_page_config']
    get_active_site_theme = helpers['get_active_site_theme']
    normalize_quota = helpers['normalize_quota']
    default_home_page_config = helpers['default_home_page_config']
    default_site_nav_items = helpers['default_site_nav_items']
    asset_style_type_options = helpers['asset_style_type_options']
    copy_persona_options = helpers['copy_persona_options']
    copy_scene_options = helpers['copy_scene_options']
    copy_direction_options = helpers['copy_direction_options']
    copy_goal_options = helpers['copy_goal_options']
    copy_product_options = helpers['copy_product_options']
    copy_skill_options = helpers['copy_skill_options']
    title_skill_options = helpers['title_skill_options']
    image_skill_options = helpers['image_skill_options']
    image_skill_presets = helpers['image_skill_presets']
    build_asset_style_recommendation_payload = helpers['build_asset_style_recommendation_payload']
    build_strategy_recommendation_payload = helpers['build_strategy_recommendation_payload']
    build_task_agent_brief_payload = helpers['build_task_agent_brief_payload']
    apply_submission_strategy_snapshot = helpers['apply_submission_strategy_snapshot']
    serialize_submission_strategy = helpers['serialize_submission_strategy']
    validate_required_platform_data = helpers['validate_required_platform_data']
    validate_partial_platform_data = helpers['validate_partial_platform_data']
    auto_detect_content_type = helpers['auto_detect_content_type']
    sync_tracking_from_submission = helpers['sync_tracking_from_submission']
    db = helpers['db']
    datetime = helpers['datetime']
    image_skill_preset_map = image_skill_presets() or {}
    copy_persona_label_map = copy_persona_options() or {}
    copy_scene_label_map = copy_scene_options() or {}
    copy_direction_label_map = copy_direction_options() or {}
    copy_goal_label_map = copy_goal_options() or {}
    copy_product_label_map = copy_product_options() or {}
    asset_style_meta_map = {
        (item.get('key') or ''): item
        for item in (asset_style_type_options() or [])
        if isinstance(item, dict)
    }
    image_template_family_meta = {
        'medical_science': {
            'label': '报告解读卡',
            'description': '适合体检单、指标说明、器官解读、检查报告翻译。',
        },
        'knowledge_card': {
            'label': '课堂笔记卡',
            'description': '适合知识拆解、误区纠偏、重点提炼和结构化讲解。',
        },
        'poster': {
            'label': '大字封面',
            'description': '适合冲点击、先抓眼球，再把正文和内页接住。',
        },
        'checklist': {
            'label': '清单卡',
            'description': '适合步骤、避坑、对照表、可收藏执行清单。',
        },
        'memo': {
            'label': '备忘录/陪伴卡',
            'description': '适合第一人称经历、陪伴型表达、情绪共鸣和复盘。',
        },
        'custom': {
            'label': '自定义模板',
            'description': '适合你自己指定画面方向，再由系统选近似模板落图。',
        },
    }

    def enrich_generator_seed_with_image_preset(seed):
        enriched = dict(seed or {})
        preset = image_skill_preset_map.get(enriched.get('image_skill') or '')
        if preset:
            enriched.setdefault('image_family_key', preset.get('family_key') or '')
            enriched.setdefault('image_mode_key', preset.get('mode_key') or '')
            enriched.setdefault('cover_style_type', preset.get('cover_style_key') or '')
            enriched.setdefault('inner_style_type', preset.get('inner_style_key') or '')
        return enriched

    def build_public_context():
        context = dict(build_public_shell_context())
        site_config = dict(context.get('site_config') or {})
        nav_items = [dict(item) for item in (site_config.get('nav_items') or [dict(item) for item in default_site_nav_items])]
        has_liver_science = any(
            (item.get('label') or '').strip() in {'肝健康科普', '肝健康IP'} or (item.get('url') or '').strip() == '/liver-science'
            for item in nav_items
        )
        if not has_liver_science:
            insert_at = next(
                (index + 1 for index, item in enumerate(nav_items) if (item.get('label') or '').strip() == '话题广场'),
                1,
            )
            nav_items.insert(insert_at, {
                'label': '肝健康IP',
                'url': '/liver-science',
                'icon': 'bi-heart-pulse',
                'target': '_self',
            })
        else:
            for item in nav_items:
                if (item.get('url') or '').strip() == '/liver-science' or (item.get('label') or '').strip() == '肝健康科普':
                    item['label'] = '肝健康IP'
        has_hot_topics = any(
            (item.get('label') or '').strip() == '热搜话题' or (item.get('url') or '').strip() == '/hot-topics'
            for item in nav_items
        )
        if not has_hot_topics:
            insert_at = next(
                (index + 1 for index, item in enumerate(nav_items) if (item.get('url') or '').strip() == '/liver-science'),
                min(len(nav_items), 2),
            )
            nav_items.insert(insert_at, {
                'label': '热搜话题',
                'url': '/hot-topics',
                'icon': 'bi-lightning-charge',
                'target': '_self',
            })
        has_image_library = any(
            (item.get('label') or '').strip() == '图片库' or (item.get('url') or '').strip() == '/image-library'
            for item in nav_items
        )
        if not has_image_library:
            insert_at = next(
                (index + 1 for index, item in enumerate(nav_items) if (item.get('label') or '').strip() == '数据分析'),
                min(len(nav_items), 3),
            )
            nav_items.insert(insert_at, {
                'label': '图片库',
                'url': '/image-library',
                'icon': 'bi-images',
                'target': '_self',
            })
        site_config['nav_items'] = nav_items[:8]
        context['site_config'] = site_config
        return context

    def serialize_public_trend(note):
        return {
            'id': note.id,
            'title': note.title or '',
            'keyword': note.keyword or '',
            'source_platform': note.source_platform or '',
            'source_channel': note.source_channel or '',
            'author': note.author or '',
            'views': note.views or 0,
            'likes': note.likes or 0,
            'favorites': note.favorites or 0,
            'comments': note.comments or 0,
            'summary': note.summary or '',
            'link': note.link or '',
            'created_at': note.created_at.strftime('%Y-%m-%d %H:%M:%S') if note.created_at else '',
        }

    def serialize_public_asset(item):
        tags = [part.strip() for part in (item.tags or '').split(',') if part.strip()]
        payload_json = load_json_value(item.raw_payload, {})
        library_type_label_map = {
            'generated': '生成资产',
            'product': '产品图库',
            'content': '内容素材库',
            'reference': '风格参考库',
        }
        return {
            'id': item.id,
            'title': item.title or '未命名图片',
            'subtitle': item.subtitle or '',
            'preview_url': item.preview_url or '',
            'product_name': item.product_name or '',
            'product_category': item.product_category or '',
            'product_indication': item.product_indication or '',
            'library_type_key': item.library_type or 'generated',
            'library_type': library_type_label_map.get(item.library_type or 'generated', item.library_type or '生成资产'),
            'asset_type': item.asset_type or '',
            'style_type_key': item.style_type_key or '',
            'visual_role': item.visual_role or '',
            'source_provider': item.source_provider or '',
            'download_name': item.download_name or '',
            'usable_score': safe_int(payload_json.get('usable_score'), 0),
            'usable_label': (payload_json.get('usable_label') or '').strip(),
            'recommended_usage': (payload_json.get('recommended_usage') or '').strip(),
            'recommended_usage_label': (payload_json.get('recommended_usage_label') or '').strip(),
            'tags': tags[:8],
            'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else '',
        }

    def serialize_public_hot_topic(item):
        lane_key = item.lane_key or ''
        persona_key = item.persona_key or ''
        lane_meta = lane_meta_map.get(lane_key, {})
        persona_meta = persona_meta_map.get(persona_key, {})
        focus_keyword = (item.keyword or item.title or '肝健康热点').strip()
        image_skill_key = LIVER_IP_LANE_TO_IMAGE_SKILL.get(lane_key or 'report_interpretation', 'high_click_cover')
        image_preset = image_skill_preset_map.get(image_skill_key) or {}
        family_key = image_preset.get('family_key') or ''
        cover_style_key = image_preset.get('cover_style_key') or ''
        inner_style_key = image_preset.get('inner_style_key') or ''
        family_meta = image_template_family_meta.get(family_key, {})
        cover_meta = asset_style_meta_map.get(cover_style_key, {})
        inner_meta = asset_style_meta_map.get(inner_style_key, {})
        hotspot_reason = (
            '平台热搜/相关搜索词，适合快速借势。'
            if (item.source_channel or '').find('热搜') >= 0
            else '已经被确认过的爆款问题，适合改造成肝健康场景内容。'
        )
        merge_strategy = [
            f'先用“{focus_keyword}”这个用户熟悉的问题做开头，不要一上来就讲产品。',
            f'中段切到“{lane_meta.get("title") or "肝健康方向"}”，把热点翻译成用户真正关心的健康问题。',
            '结尾给 3 个以内可执行动作，再自然带出长期管理或检查建议。',
        ]
        title_ideas = [
            f'{focus_keyword}这件事，很多人第一步就做错了',
            f'如果你最近也在搜“{focus_keyword}”，先看这 3 点',
            f'{focus_keyword}能不能做？从肝健康角度讲清楚',
        ]
        hook_hint = (
            f'开头先接住热点情绪或问题，比如“最近很多人在搜 {focus_keyword}，'
            '但真正该关心的点不是表面那个问题。”'
        )
        cover_hint = (
            f'封面优先突出问题句“{focus_keyword}”，'
            f'视觉更适合 {lane_meta.get("title") or "肝健康"} 风格，副标题再放结果导向或避坑提醒。'
        )
        generator_seed = enrich_generator_seed_with_image_preset({
            'direction_key': lane_key or 'report_interpretation',
            'persona_key': LIVER_IP_BACKGROUND_TO_PERSONA_KEY.get(persona_key or 'patient', 'patient_self'),
            'scene_key': LIVER_IP_LANE_TO_SCENE_KEY.get(lane_key or 'report_interpretation', 'daily_liver_care'),
            'copy_goal': 'viral_title',
            'copy_skill': LIVER_IP_LANE_TO_COPY_SKILL.get(lane_key or 'report_interpretation', 'story_empathy'),
            'title_skill': LIVER_IP_LANE_TO_TITLE_SKILL.get(lane_key or 'report_interpretation', 'result_first'),
            'image_skill': image_skill_key,
            'user_prompt_seed': (
                f'请围绕“小红书热点：{focus_keyword}”来写，方向偏{lane_meta.get("title") or "肝健康内容"}，'
                f'更适合{persona_meta.get("title") or "肝健康创作者"}来讲。先接热点，再自然切入肝健康，'
                '不要硬蹭，不要硬广，最后给用户可执行建议。'
            )[:500],
        })
        return {
            'id': item.id,
            'title': item.title or '',
            'keyword': item.keyword or '',
            'source_platform': item.source_platform or '',
            'source_channel': item.source_channel or '',
            'reference_url': item.reference_url or '',
            'summary': item.summary or '',
            'hot_score': item.hot_score or 0,
            'lane_key': item.lane_key or '',
            'lane_title': lane_meta_map.get(item.lane_key or '', {}).get('title') or '',
            'persona_key': item.persona_key or '',
            'persona_title': persona_meta_map.get(item.persona_key or '', {}).get('title') or '',
            'audience_hint': item.audience_hint or '',
            'integration_hint': item.integration_hint or '',
            'usage_tip': item.usage_tip or '',
            'hotspot_reason': hotspot_reason,
            'merge_strategy': merge_strategy,
            'title_ideas': title_ideas,
            'hook_hint': hook_hint,
            'cover_hint': cover_hint,
            'image_skill_label': image_preset.get('label') or '',
            'template_agent_label': family_meta.get('label') or '',
            'template_agent_description': family_meta.get('description') or '',
            'cover_style_label': cover_meta.get('label') or cover_style_key,
            'inner_style_label': inner_meta.get('label') or inner_style_key,
            'generator_seed': generator_seed,
            'status': item.status or 'active',
            'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else '',
        }

    persona_meta_map = {
        item['key']: item
        for item in LIVER_SCIENCE_PERSONA_LANES
    }

    def serialize_public_corpus(entry):
        tags = [part.strip() for part in (entry.tags or '').split(',') if part.strip()]
        template_label_map = {
            'checklist': '清单模板',
            'myth_busting': '误区纠正',
            'comparison': '对比拆解',
            'process': '流程步骤',
            'qna': '问答答疑',
            'case_story': '案例故事',
            'standard_explain': '标准说明',
        }
        template_type_key = getattr(entry, 'template_type_key', '') or ''
        lane_key = infer_corpus_lane_key(entry)
        persona_key = infer_liver_science_persona_key(' '.join([
            entry.title or '',
            getattr(entry, 'source_title', '') or '',
            entry.tags or '',
            entry.content or '',
        ]))
        return {
            'id': entry.id,
            'title': entry.title or '未命名科普内容',
            'category': entry.category or '医学科普',
            'source': entry.source or '',
            'source_title': getattr(entry, 'source_title', '') or '',
            'reference_url': getattr(entry, 'reference_url', '') or '',
            'template_type_key': template_type_key,
            'template_type_label': template_label_map.get(template_type_key, template_type_key),
            'lane_key': lane_key,
            'lane_title': lane_meta_map.get(lane_key, {}).get('title') or '',
            'persona_key': persona_key,
            'persona_title': persona_meta_map.get(persona_key, {}).get('title') or '',
            'is_auto_template': (entry.source or '') == '热点爆款转模板',
            'content': entry.content or '',
            'tags': tags[:8],
            'created_at': entry.created_at.strftime('%Y-%m-%d %H:%M:%S') if entry.created_at else '',
        }

    lane_meta_map = {
        item['key']: item
        for item in LIVER_SCIENCE_IP_LANES
    }

    def build_public_topic_recommendation(topic):
        if not topic:
            return {}
        text = ' '.join(filter(None, [
            topic.topic_name or '',
            topic.keywords or '',
            topic.direction or '',
            topic.reference_content or '',
        ]))
        lane_key = infer_liver_science_lane_key(text)
        persona_key = infer_liver_science_persona_key(text)
        lane_meta = lane_meta_map.get(lane_key, {})
        persona_meta = persona_meta_map.get(persona_key, {})
        available = max((topic.quota or 0) - (topic.filled or 0), 0)
        quota = max(topic.quota or 0, 0)
        fill_ratio = ((topic.filled or 0) / quota) if quota else 0

        score = 58
        if available <= 0:
            score = 0
        else:
            score += min(available, 18)
            if quota and fill_ratio <= 0.35:
                score += 10
            elif quota and fill_ratio <= 0.7:
                score += 4
            else:
                score -= 6
            if (topic.source_type or '') in {'topic_idea', 'trend_note'}:
                score += 10
            if any(token in text for token in ['体检', '检查', '报告', '转氨酶', 'FibroScan', '福波看', '肝弹']):
                score += 10
            if any(token in text for token in ['误区', '为什么', '别再', '是不是', '搞错']):
                score += 8
            if any(token in text for token in ['脂肪肝', '减脂', '饮食', '运动', '体重']):
                score += 6
            if (topic.reference_link or '').strip():
                score += 4
            if (topic.reference_content or '').strip() or (topic.writing_example or '').strip():
                score += 4
        score = max(min(int(score), 100), 0)

        if available <= 0:
            recommendation_label = '已满'
        elif score >= 88:
            recommendation_label = '优先报名'
        elif score >= 74:
            recommendation_label = '推荐报名'
        else:
            recommendation_label = '可补位'

        if lane_key == 'report_interpretation':
            recommended_goal = '收藏种草优先'
        elif lane_key == 'myth_busting':
            recommended_goal = '爆款点击优先'
        elif lane_key in {'emotion_mindbody', 'family_care'}:
            recommended_goal = '评论互动优先'
        else:
            recommended_goal = '均衡输出'

        if available <= 0:
            recommendation_reason = '当前名额已满，建议进入下一期或做同类补位题。'
        elif score >= 88:
            recommendation_reason = '当前更适合优先分发，热度、执行价值和剩余名额都更匹配。'
        elif score >= 74:
            recommendation_reason = '当前适合作为常规推荐题，适合快速开工。'
        else:
            recommendation_reason = '当前更适合作为补位题，建议放在优先题后面分发。'

        return {
            'recommendation_score': score,
            'recommendation_label': recommendation_label,
            'recommendation_reason': recommendation_reason,
            'lane_key': lane_key,
            'lane_title': lane_meta.get('title') or '',
            'persona_key': persona_key,
            'persona_title': persona_meta.get('title') or '',
            'recommended_goal': recommended_goal,
            'available': available,
        }

    def serialize_public_topic(topic):
        return {
            **serialize_topic(topic),
            **build_public_topic_recommendation(topic),
        }

    def is_liver_science_text(text):
        haystack = (text or '').strip()
        return any(keyword in haystack for keyword in LIVER_SCIENCE_PUBLIC_KEYWORDS)

    def infer_liver_science_lane_key(text=''):
        joined = (text or '').strip()
        if any(token in joined for token in ['中医', '肝气郁结', '肝郁', '肝胆湿热', '疏肝理气', '养肝', '肝火', '肝阴']):
            return 'tcm_conditioning'
        if any(token in joined for token in ['情绪', '焦虑', '压力', '失眠', '熬夜', '睡眠', '郁结']):
            return 'emotion_mindbody'
        if any(token in joined for token in ['脂肪肝', '减脂', '体重', '饮食', '代谢']):
            return 'fatty_liver_management'
        if any(token in joined for token in ['体检', '检查', '指标', '转氨酶', 'FibroScan', '福波看', '肝弹', 'B超', '复查']):
            return 'report_interpretation'
        if any(token in joined for token in ['误区', '别再', '不是这样', '搞错', '避坑', '反常识']):
            return 'myth_busting'
        if any(token in joined for token in ['父母', '家人', '家属', '陪诊', '照护', '老人']):
            return 'family_care'
        if any(token in joined for token in ['女性', '经期', '更年期', '姨妈']):
            return 'women_health'
        if any(token in joined for token in ['运动', '健身', '跑步', '走路', '力量', '减脂训练']):
            return 'exercise_fitness'
        if any(token in joined for token in ['吃什么', '食谱', '营养', '早餐', '晚餐', '饮食建议']):
            return 'diet_nutrition'
        if any(token in joined for token in ['护肝', '保肝', '作息', '应酬', '饮酒', '习惯']):
            return 'liver_care_habits'
        return 'report_interpretation'

    def infer_science_trend_angle(note):
        text = ' '.join([
            note.keyword or '',
            note.title or '',
            note.summary or '',
        ])
        lane_key = infer_liver_science_lane_key(text)
        return lane_meta_map.get(lane_key, {}).get('title') or '健康科普'

    def infer_liver_science_persona_key(text=''):
        joined = (text or '').strip()
        if any(token in joined for token in ['父母', '家人', '家属', '陪诊', '照护', '老人']):
            return 'family'
        if any(token in joined for token in ['中医', '肝气郁结', '肝郁', '疏肝理气', '肝胆湿热', '养肝']):
            return 'tcm'
        if any(token in joined for token in ['运动', '健身', '跑步', '力量', '减脂训练']):
            return 'fitness'
        if any(token in joined for token in ['饮食', '营养', '减脂餐', '早餐', '食谱', '控糖', '控油']):
            return 'nutrition'
        if any(token in joined for token in ['女性', '经期', '更年期', '姨妈']):
            return 'women'
        if any(token in joined for token in ['上班', '职场', '久坐', '加班', '应酬']):
            return 'office'
        if any(token in joined for token in ['体检', '报告', '指标', 'FibroScan', '福波看', '肝弹', '科普', '问答']):
            return 'medical'
        return 'patient'

    def infer_corpus_lane_key(entry):
        text = ' '.join([
            entry.title or '',
            entry.category or '',
            entry.tags or '',
            entry.content or '',
            getattr(entry, 'source_title', '') or '',
        ])
        return infer_liver_science_lane_key(text)

    def build_lane_groups(items, lane_key_getter, serializer, *, item_limit=3, score_func=None):
        groups = {}
        for item in items:
            lane_key = lane_key_getter(item)
            lane_meta = lane_meta_map.get(lane_key)
            if not lane_meta:
                continue
            item_score = score_func(item) if score_func else 0
            row = groups.setdefault(lane_key, {
                'key': lane_key,
                'title': lane_meta['title'],
                'description': lane_meta['description'],
                'tags': lane_meta['tags'],
                'count': 0,
                'score': 0,
                'items': [],
            })
            row['count'] += 1
            row['score'] += item_score
            if len(row['items']) < item_limit:
                row['items'].append(serializer(item))
        rows = list(groups.values())
        rows.sort(key=lambda item: (item['score'], item['count'], item['title']), reverse=True)
        return rows

    def build_ip_column_plans(trend_groups, template_groups, top_keywords):
        trend_count_map = {row['key']: row['count'] for row in trend_groups}
        template_count_map = {row['key']: row['count'] for row in template_groups}
        trend_score_map = {row['key']: row.get('score', 0) for row in trend_groups}
        template_score_map = {row['key']: row.get('score', 0) for row in template_groups}
        rows = []
        for lane in LIVER_SCIENCE_IP_LANES:
            key = lane['key']
            blueprint = LIVER_IP_COLUMN_BLUEPRINTS.get(key, {})
            hotness = (trend_score_map.get(key, 0) * 2) + template_score_map.get(key, 0)
            sample_titles = []
            for source_rows in [trend_groups, template_groups]:
                current = next((item for item in source_rows if item['key'] == key), None)
                if not current:
                    continue
                for sample in current['items'][:2]:
                    title = sample.get('title') or ''
                    if title and title not in sample_titles:
                        sample_titles.append(title)
            rows.append({
                'key': key,
                'title': blueprint.get('title') or lane['title'],
                'description': lane['description'],
                'audience': blueprint.get('audience') or '肝健康关注人群',
                'cadence': blueprint.get('cadence') or '每周 1-2 条',
                'personas': blueprint.get('personas') or [],
                'hotness': hotness,
                'trend_count': trend_count_map.get(key, 0),
                'template_count': template_count_map.get(key, 0),
                'trend_score': trend_score_map.get(key, 0),
                'template_score': template_score_map.get(key, 0),
                'sample_titles': sample_titles[:3],
                'tags': lane['tags'][:4],
                'keyword_hint': top_keywords[:3] if key in {'report_interpretation', 'fatty_liver_management', 'tcm_conditioning'} else top_keywords[3:6],
            })
        rows.sort(key=lambda item: (item['hotness'], item['trend_count'], item['template_count']), reverse=True)
        return rows[:6]

    def build_lane_overview_rows(trend_groups, template_groups):
        trend_map = {row['key']: row for row in trend_groups}
        template_map = {row['key']: row for row in template_groups}
        rows = []
        for lane in LIVER_SCIENCE_IP_LANES:
            trend_row = trend_map.get(lane['key'], {})
            template_row = template_map.get(lane['key'], {})
            sample_items = []
            for item in (trend_row.get('items') or [])[:2]:
                sample_items.append(item)
            for item in (template_row.get('items') or [])[:1]:
                sample_items.append(item)
            rows.append({
                'key': lane['key'],
                'title': lane['title'],
                'description': lane['description'],
                'tags': lane['tags'],
                'trend_count': trend_row.get('count', 0),
                'template_count': template_row.get('count', 0),
                'hotness': (trend_row.get('score', 0) * 2) + template_row.get('score', 0),
                'items': sample_items[:3],
            })
        rows.sort(key=lambda item: (item['hotness'], item['trend_count'], item['template_count']), reverse=True)
        return rows[:6]

    def build_liver_science_dataset():
        science_entries = CorpusEntry.query.filter_by(status='active').filter(
            CorpusEntry.category.in_(['医学科普', '合规表达'])
        ).order_by(
            CorpusEntry.usage_count.desc(),
            CorpusEntry.updated_at.desc(),
            CorpusEntry.id.desc(),
        ).limit(24).all()
        if not science_entries:
            science_entries = CorpusEntry.query.filter_by(status='active').order_by(
                CorpusEntry.usage_count.desc(),
                CorpusEntry.updated_at.desc(),
                CorpusEntry.id.desc(),
            ).limit(24).all()

        template_candidates = CorpusEntry.query.filter_by(status='active').filter(
            CorpusEntry.category.in_(['爆款拆解', '封面模板', '产品卖点'])
        ).filter(
            (CorpusEntry.reference_url.isnot(None) & (CorpusEntry.reference_url != '')) |
            CorpusEntry.tags.contains('话题参考链接')
        ).order_by(
            CorpusEntry.updated_at.desc(),
            CorpusEntry.id.desc(),
        ).limit(80).all()
        template_entries = sorted(
            template_candidates,
            key=lambda item: (_template_priority_score(item), item.updated_at or item.created_at or datetime.min),
            reverse=True,
        )[:18]

        trend_candidates = TrendNote.query.filter(TrendNote.pool_status != 'archived').order_by(
            TrendNote.hot_score.desc(),
            TrendNote.created_at.desc(),
            TrendNote.id.desc(),
        ).limit(180).all()
        science_trends = [
            note for note in trend_candidates
            if is_liver_science_text(' '.join([note.keyword or '', note.title or '', note.summary or '']))
        ][:18]

        top_keywords = []
        seen_keywords = set()
        for note in science_trends:
            keyword = (note.keyword or '').strip()
            if not keyword or keyword in seen_keywords:
                continue
            top_keywords.append(keyword)
            seen_keywords.add(keyword)
            if len(top_keywords) >= 8:
                break

        trend_groups = build_lane_groups(
            science_trends,
            lambda note: infer_liver_science_lane_key(' '.join([note.keyword or '', note.title or '', note.summary or ''])),
            serialize_science_trend,
            score_func=_trend_priority_score,
        )
        template_groups = build_lane_groups(
            template_entries,
            infer_corpus_lane_key,
            serialize_public_corpus,
            score_func=_template_priority_score,
        )
        lane_overview_rows = build_lane_overview_rows(trend_groups, template_groups)
        column_plans = build_ip_column_plans(trend_groups, template_groups, top_keywords)
        recent_auto_templates = [
            serialize_public_corpus(item)
            for item in sorted(
                [entry for entry in template_entries if (entry.source or '') == '热点爆款转模板'],
                key=lambda item: (item.updated_at or item.created_at or datetime.min),
                reverse=True,
            )[:6]
        ]
        return {
            'science_entries': science_entries,
            'template_entries': template_entries,
            'science_trends': science_trends,
            'top_keywords': top_keywords,
            'trend_groups': trend_groups,
            'template_groups': template_groups,
            'lane_overview_rows': lane_overview_rows,
            'column_plans': column_plans,
            'recent_auto_templates': recent_auto_templates,
        }

    def build_liver_ip_agent_plan(payload=None):
        payload = payload or {}
        dataset = build_liver_science_dataset()
        note = (payload.get('profile_note') or '').strip()
        preferred_lane_key = (payload.get('preferred_lane_key') or 'auto').strip()
        background_key = (payload.get('background_key') or 'patient').strip()
        goal_key = (payload.get('goal_key') or 'trust').strip()
        cadence = (payload.get('weekly_cadence') or '每周 2 条').strip()

        lane_key = preferred_lane_key if preferred_lane_key != 'auto' else infer_liver_science_lane_key(note)
        lane_meta = lane_meta_map.get(lane_key, LIVER_SCIENCE_IP_LANES[0])
        related_lane_keys = [lane_key] + LIVER_IP_LANE_RELATIONS.get(lane_key, [])[:2]
        column_lookup = {item['key']: item for item in dataset['column_plans']}
        recommended_columns = []
        for key in related_lane_keys:
            if key in column_lookup:
                recommended_columns.append(column_lookup[key])
            else:
                lane = lane_meta_map.get(key)
                blueprint = LIVER_IP_COLUMN_BLUEPRINTS.get(key, {})
                if lane:
                    recommended_columns.append({
                        'key': key,
                        'title': blueprint.get('title') or lane['title'],
                        'description': lane['description'],
                        'audience': blueprint.get('audience') or '肝健康关注人群',
                        'cadence': blueprint.get('cadence') or cadence,
                        'personas': blueprint.get('personas') or [],
                        'sample_titles': [],
                        'tags': lane['tags'][:4],
                        'keyword_hint': dataset['top_keywords'][:3],
                    })

        case_refs = []
        trend_group_lookup = {item['key']: item for item in dataset['trend_groups']}
        for key in related_lane_keys:
            group = trend_group_lookup.get(key)
            if not group:
                continue
            for item in group['items'][:2]:
                case_refs.append(item)
        case_refs = case_refs[:5]

        template_refs = []
        template_group_lookup = {item['key']: item for item in dataset['template_groups']}
        for key in related_lane_keys:
            group = template_group_lookup.get(key)
            if not group:
                continue
            for item in group['items'][:2]:
                template_refs.append(item)
        template_refs = template_refs[:4]

        background_label = LIVER_IP_BACKGROUND_OPTIONS.get(background_key, background_key or '肝健康创作者')
        goal_label = LIVER_IP_GOAL_OPTIONS.get(goal_key, goal_key or '建立专业信任')
        starter_titles = []
        lane_keyword = (dataset['top_keywords'][0] if dataset['top_keywords'] else lane_meta['tags'][0]) if lane_meta.get('tags') else '肝健康'
        for seed in [
            f'{lane_keyword}这件事很多人第一步就做错了',
            f'如果你也在意{lane_keyword}，先看这3点',
            f'我会先从{lane_meta["title"]}切入，做一条能收藏的内容',
            f'{lane_meta["title"]}更适合怎么做成长更稳的栏目',
            f'关于{lane_keyword}，这类人群最容易忽略什么',
        ]:
            if seed not in starter_titles:
                starter_titles.append(seed)
        starter_titles = starter_titles[:5]

        positioning = (
            f'你当前更适合把账号做成“{background_label} + {lane_meta["title"]}”的肝健康IP，'
            f'先用 {goal_label} 作为阶段目标，不急着什么都写，而是围绕 3 条栏目线稳定更新。'
        )
        next_steps = [
            '先选 1 条主栏目 + 2 条辅助栏目，连续发 2 周，不要一开始铺太宽。',
            '每条内容优先解决一个具体问题，避免把一篇写成大而全。',
            '先从你自己最能持续讲的视角开始，再逐步拓展到更专业的方向。',
        ]
        if note:
            next_steps.insert(0, f'你当前提到的重点是：{note[:48]}，建议先围绕这个真实优势或兴趣点起步。')

        generator_seed = enrich_generator_seed_with_image_preset({
            'direction_key': lane_key,
            'persona_key': LIVER_IP_BACKGROUND_TO_PERSONA_KEY.get(background_key, 'patient_self'),
            'scene_key': LIVER_IP_LANE_TO_SCENE_KEY.get(lane_key, 'daily_liver_care'),
            'copy_goal': 'trust_building' if goal_key == 'trust' else ('viral_title' if goal_key == 'growth' else ('comment_engagement' if goal_key == 'consulting' else 'balanced')),
            'copy_skill': LIVER_IP_LANE_TO_COPY_SKILL.get(lane_key, 'story_empathy'),
            'title_skill': LIVER_IP_LANE_TO_TITLE_SKILL.get(lane_key, 'result_first'),
            'image_skill': LIVER_IP_LANE_TO_IMAGE_SKILL.get(lane_key, 'high_click_cover'),
            'user_prompt_seed': (
                f"请按“{lane_meta['title']}”来写，账号更像“{background_label}”，"
                f"目标是{goal_label}，表达更像个人IP而不是教科书。"
                f"{(' 重点围绕：' + note) if note else ''}"
            )[:500],
        })

        return {
            'success': True,
            'recommended_lane': {
                'key': lane_key,
                'title': lane_meta['title'],
                'description': lane_meta['description'],
            },
            'background_label': background_label,
            'goal_label': goal_label,
            'cadence': cadence,
            'positioning': positioning,
            'recommended_columns': recommended_columns[:3],
            'case_refs': case_refs,
            'template_refs': template_refs,
            'starter_titles': starter_titles,
            'next_steps': next_steps[:4],
            'generator_seed': generator_seed,
        }

    def serialize_liver_ip_profile_plan(item):
        if not item:
            return {}
        try:
            plan_payload = json.loads(item.plan_payload or '{}')
        except Exception:
            plan_payload = {}
        try:
            generator_seed = json.loads(item.generator_seed_payload or '{}')
        except Exception:
            generator_seed = {}
        return {
            'id': item.id,
            'profile_key': item.profile_key,
            'background_key': item.background_key or '',
            'preferred_lane_key': item.preferred_lane_key or '',
            'goal_key': item.goal_key or '',
            'weekly_cadence': item.weekly_cadence or '',
            'profile_note': item.profile_note or '',
            'plan_payload': plan_payload if isinstance(plan_payload, dict) else {},
            'generator_seed': generator_seed if isinstance(generator_seed, dict) else {},
            'last_used_at': item.last_used_at.strftime('%Y-%m-%d %H:%M:%S') if item.last_used_at else '',
            'updated_at': item.updated_at.strftime('%Y-%m-%d %H:%M:%S') if item.updated_at else '',
        }

    def save_liver_ip_profile_plan(profile_key, payload, plan_result):
        key = (profile_key or '').strip() or uuid4().hex
        record = LiverIpProfilePlan.query.filter_by(profile_key=key).first()
        if not record:
            record = LiverIpProfilePlan(profile_key=key)
            db.session.add(record)

        record.background_key = (payload.get('background_key') or '').strip()[:50]
        record.preferred_lane_key = (payload.get('preferred_lane_key') or '').strip()[:50]
        record.goal_key = (payload.get('goal_key') or '').strip()[:50]
        record.weekly_cadence = (payload.get('weekly_cadence') or '').strip()[:50]
        record.profile_note = (payload.get('profile_note') or '').strip()[:2000]
        record.plan_payload = json.dumps(plan_result, ensure_ascii=False)
        record.generator_seed_payload = json.dumps(plan_result.get('generator_seed') or {}, ensure_ascii=False)
        record.last_used_at = datetime.now()
        db.session.flush()
        return record

    def serialize_science_trend(note):
        interactions = (note.likes or 0) + (note.favorites or 0) + (note.comments or 0)
        lane_key = infer_liver_science_lane_key(' '.join([
            note.keyword or '',
            note.title or '',
            note.summary or '',
        ]))
        persona_key = infer_liver_science_persona_key(' '.join([
            note.keyword or '',
            note.title or '',
            note.summary or '',
        ]))
        return {
            **serialize_public_trend(note),
            'interactions': interactions,
            'angle': infer_science_trend_angle(note),
            'lane_key': lane_key,
            'lane_title': lane_meta_map.get(lane_key, {}).get('title') or '',
            'persona_key': persona_key,
            'persona_title': persona_meta_map.get(persona_key, {}).get('title') or '',
        }

    def _trend_priority_score(note):
        return (
            (note.hot_score or 0) * 3 +
            (note.likes or 0) +
            (note.favorites or 0) * 2 +
            (note.comments or 0) * 3 +
            min((note.views or 0) // 100, 200)
        )

    def _template_priority_score(entry):
        score = (entry.usage_count or 0) * 5
        if (entry.source or '') == '热点爆款转模板':
            score += 80
        if getattr(entry, 'reference_url', ''):
            score += 20
        updated_at = getattr(entry, 'updated_at', None)
        if updated_at:
            age_days = max((datetime.now() - updated_at).days, 0)
            if age_days <= 7:
                score += 40
            elif age_days <= 30:
                score += 20
        return score

    def _asset_task_status_label(status=''):
        return {
            'queued': '待出图',
            'running': '出图中',
            'success': '已出图',
            'failed': '出图失败',
        }.get((status or '').strip(), '未出图')

    def _task_status_priority(status_key=''):
        return {
            'pending_publish': 0,
            'generated': 1,
            'strategy_ready': 2,
            'not_generated': 3,
            'syncing': 4,
            'published': 5,
        }.get((status_key or '').strip(), 9)

    def _build_registration_task_summary(registration, tracking_summary=None):
        submission = getattr(registration, 'submission', None)
        tracking_summary = tracking_summary or {}
        base_task_url = f'/register_success/{registration.id}'
        strategy = serialize_submission_strategy(submission) if submission else {}
        generator_context = strategy.get('generator_context') if isinstance(strategy.get('generator_context'), dict) else {}
        latest_asset_task = db.session.query(
            AssetGenerationTask.id.label('id'),
            AssetGenerationTask.status.label('status'),
            AssetGenerationTask.updated_at.label('updated_at'),
            AssetGenerationTask.created_at.label('created_at'),
        ).filter(
            AssetGenerationTask.registration_id == registration.id,
        ).order_by(
            AssetGenerationTask.updated_at.desc(),
            AssetGenerationTask.created_at.desc(),
            AssetGenerationTask.id.desc(),
        ).first()
        asset_library_count = db.session.query(db.func.count(AssetLibrary.id)).filter(
            AssetLibrary.registration_id == registration.id,
            AssetLibrary.pool_status != 'archived',
        ).scalar() or 0

        has_strategy_plan = bool(submission and any([
            (strategy.get('selected_persona_key') or '').strip(),
            (strategy.get('selected_scene_key') or '').strip(),
            (strategy.get('selected_direction_key') or '').strip(),
            (strategy.get('selected_product_key') or '').strip(),
            (strategy.get('selected_agent_copy_route_id') or '').strip(),
            (strategy.get('selected_agent_image_route_id') or '').strip(),
            (strategy.get('selected_image_agent_plan_id') or '').strip(),
        ]))
        has_selected_copy = bool(submission and any([
            (submission.selected_copy_text or '').strip(),
            (submission.selected_title or '').strip(),
        ]))
        has_generated_asset = asset_library_count > 0 or bool(
            latest_asset_task and latest_asset_task.status in {'queued', 'running', 'success'}
        )
        has_submission_link = bool(submission and (submission.xhs_link or '').strip())
        has_synced_metrics = bool(submission and any([
            submission.xhs_views or 0,
            submission.xhs_likes or 0,
            submission.xhs_favorites or 0,
            submission.xhs_comments or 0,
        ]))
        tracking_status = (tracking_summary.get('status') or '').strip()
        has_tracking_progress = bool(tracking_summary and any([
            tracking_summary.get('current_month_post_count') or 0,
            tracking_summary.get('total_post_count') or 0,
            tracking_summary.get('last_synced_at') or '',
        ]))

        if has_submission_link:
            if has_synced_metrics or has_tracking_progress or tracking_status == 'tracking':
                status_key = 'published'
                status_label = '已发布'
                status_badge_class = 'bg-success'
                status_note = '笔记链接已提交，系统已经拿到发布结果或同步数据。'
                action_label = '查看任务与数据'
                action_url = f'{base_task_url}#submitForm'
            else:
                status_key = 'syncing'
                status_label = '数据更新中'
                status_badge_class = 'bg-primary'
                status_note = tracking_summary.get('message') or '笔记链接已提交，系统正在同步账号和互动数据。'
                action_label = '去更新数据'
                action_url = f'{base_task_url}#submitForm'
        elif has_selected_copy:
            status_key = 'pending_publish'
            status_label = '待发布'
            status_badge_class = 'bg-warning text-dark'
            status_note = '文案方案已经确定，下一步去发布笔记并回填链接。'
            action_label = '去提交链接'
            action_url = f'{base_task_url}#submitForm'
        elif has_strategy_plan:
            status_key = 'strategy_ready'
            status_label = '已选策略'
            status_badge_class = 'bg-light text-dark'
            status_note = '已经选好人设、场景或路线，下一步生成文案和图片。'
            action_label = '去生成内容'
            action_url = f'{base_task_url}#copyStudio'
        elif has_generated_asset:
            status_key = 'generated'
            status_label = '已生成'
            status_badge_class = 'bg-info text-dark'
            status_note = (
                f'已生成 {asset_library_count} 张图片，最近图片任务状态：{_asset_task_status_label(getattr(latest_asset_task, "status", ""))}。'
                if asset_library_count or latest_asset_task else
                '已经开始生成图文内容，可以继续确认并完善。'
            )
            action_label = '继续完善内容'
            action_url = f'{base_task_url}#copyStudio'
        else:
            status_key = 'not_generated'
            status_label = '未生成'
            status_badge_class = 'bg-secondary'
            status_note = '还没有生成文案或图片，建议先进入任务详情生成内容。'
            action_label = '去生成内容'
            action_url = f'{base_task_url}#copyStudio'

        strategy_summary_items = []
        if generator_context.get('persona'):
            strategy_summary_items.append(f"人设：{generator_context.get('persona')}")
        if generator_context.get('scene'):
            strategy_summary_items.append(f"场景：{generator_context.get('scene')}")
        if generator_context.get('goal'):
            strategy_summary_items.append(f"目标：{generator_context.get('goal')}")
        if generator_context.get('selected_copy_route_label'):
            strategy_summary_items.append(f"文案路线：{generator_context.get('selected_copy_route_label')}")
        if generator_context.get('selected_image_route_label'):
            strategy_summary_items.append(f"图片路线：{generator_context.get('selected_image_route_label')}")
        if not strategy_summary_items and strategy:
            if strategy.get('selected_persona_key'):
                strategy_summary_items.append(f"人设：{copy_persona_label_map.get(strategy.get('selected_persona_key'), strategy.get('selected_persona_key'))}")
            if strategy.get('selected_scene_key'):
                strategy_summary_items.append(f"场景：{copy_scene_label_map.get(strategy.get('selected_scene_key'), strategy.get('selected_scene_key'))}")
            if strategy.get('selected_direction_key'):
                strategy_summary_items.append(f"方向：{copy_direction_label_map.get(strategy.get('selected_direction_key'), strategy.get('selected_direction_key'))}")
            if strategy.get('selected_product_key'):
                strategy_summary_items.append(f"产品：{copy_product_label_map.get(strategy.get('selected_product_key'), strategy.get('selected_product_key'))}")
            if strategy.get('selected_copy_goal'):
                strategy_summary_items.append(f"目标：{copy_goal_label_map.get(strategy.get('selected_copy_goal'), strategy.get('selected_copy_goal'))}")
            if strategy.get('selected_copy_skill'):
                strategy_summary_items.append(f"文案：{copy_skill_options().get(strategy.get('selected_copy_skill'), strategy.get('selected_copy_skill'))}")
            if strategy.get('selected_title_skill'):
                strategy_summary_items.append(f"标题：{title_skill_options().get(strategy.get('selected_title_skill'), strategy.get('selected_title_skill'))}")
            if strategy.get('selected_image_skill'):
                strategy_summary_items.append(f"图片：{image_skill_options().get(strategy.get('selected_image_skill'), strategy.get('selected_image_skill'))}")

        return {
            'status_key': status_key,
            'status_priority': _task_status_priority(status_key),
            'status_label': status_label,
            'status_badge_class': status_badge_class,
            'status_note': status_note,
            'action_label': action_label,
            'action_url': action_url,
            'task_url': base_task_url,
            'task_target': '_self',
            'note_url': (submission.xhs_link or '').strip() if submission else '',
            'note_target': '_blank',
            'has_strategy_plan': has_strategy_plan,
            'has_selected_copy': has_selected_copy,
            'has_generated_asset': has_generated_asset,
            'generated_asset_count': asset_library_count,
            'latest_asset_status_label': _asset_task_status_label(getattr(latest_asset_task, 'status', '')),
            'tracking_status_label': tracking_summary.get('status_label') or '',
            'strategy_summary_items': strategy_summary_items[:5],
            'steps': [
                {'label': '策略选择', 'done': has_strategy_plan},
                {'label': '内容生成', 'done': bool(has_selected_copy or has_generated_asset)},
                {'label': '提交链接', 'done': has_submission_link},
                {'label': '数据同步', 'done': bool(has_synced_metrics or has_tracking_progress or tracking_status == 'tracking')},
            ],
        }

    def _build_task_workspace_summary(registrations, task_summaries=None):
        task_summaries = task_summaries or {}
        items = []
        for reg in registrations or []:
            task = task_summaries.get(reg.id) or {}
            if not task:
                continue
            items.append({
                'registration_id': reg.id,
                'topic_name': reg.topic.topic_name if getattr(reg, 'topic', None) else '未命名任务',
                **task,
            })

        total = len(items)
        status_counts = {
            'not_generated': len([item for item in items if item.get('status_key') == 'not_generated']),
            'strategy_ready': len([item for item in items if item.get('status_key') == 'strategy_ready']),
            'generated': len([item for item in items if item.get('status_key') == 'generated']),
            'pending_publish': len([item for item in items if item.get('status_key') == 'pending_publish']),
            'syncing': len([item for item in items if item.get('status_key') == 'syncing']),
            'published': len([item for item in items if item.get('status_key') == 'published']),
        }
        active_count = total - status_counts['published']
        completion_rate = round((status_counts['published'] / total) * 100, 1) if total else 0

        focus_priority = ['pending_publish', 'generated', 'strategy_ready', 'not_generated', 'syncing', 'published']
        focus_item = None
        for status_key in focus_priority:
            focus_item = next((item for item in items if item.get('status_key') == status_key), None)
            if focus_item:
                break

        focus_message_map = {
            'pending_publish': '这条任务已经接近完成，优先去发布并提交链接，最容易形成闭环。',
            'generated': '这条任务已经产出内容，优先补齐最后确认和发布动作。',
            'strategy_ready': '这条任务已经选好推荐策略，下一步直接生成文案和图片，不要再停留在选择阶段。',
            'not_generated': '这条任务还没开始生成内容，建议先把第一条内容做出来。',
            'syncing': '这条任务已经提交链接，当前重点是观察同步结果并补齐最新数据。',
            'published': '当前任务都已进入发布阶段，可以回头复盘表现最好的那一条。',
        }

        return {
            'total': total,
            'active_count': active_count,
            'completion_rate': completion_rate,
            'counts': status_counts,
            'focus_item': focus_item,
            'focus_message': focus_message_map.get((focus_item or {}).get('status_key'), ''),
        }

    def render_my_registration_page(registrations=None, error=''):
        registrations = registrations or []
        tracking_summaries = {
            reg.id: build_registration_tracking_summary(reg)
            for reg in registrations
        }
        task_summaries = {
            reg.id: _build_registration_task_summary(reg, tracking_summary=tracking_summaries.get(reg.id) or {})
            for reg in registrations
        }
        registrations = sorted(
            registrations,
            key=lambda reg: (
                (task_summaries.get(reg.id) or {}).get('status_priority', 9),
                -reg.id,
            ),
        )
        task_workspace_summary = _build_task_workspace_summary(registrations, task_summaries=task_summaries)
        return render_template(
            'my_registration.html',
            registrations=registrations,
            error=error,
            tracking_summaries=tracking_summaries,
            task_summaries=task_summaries,
            task_workspace_summary=task_workspace_summary,
            **build_public_context(),
        )

    @app.route('/')
    def index():
        activity = Activity.query.filter_by(status='published').order_by(Activity.created_at.desc()).first()
        if not activity:
            activities = Activity.query.order_by(Activity.created_at.desc()).all()
            if activities:
                activity = activities[0]

        public_context = build_public_context()
        site_config = dict(public_context.get('site_config') or {})
        site_theme = dict(public_context.get('site_theme') or {})

        split_index = normalize_quota(
            site_config.get('primary_topic_limit'),
            default=default_home_page_config['primary_topic_limit'],
            min_value=1,
            max_value=120,
        )
        all_topics = list(activity.topics) if activity else []
        all_topics = sorted(
            all_topics,
            key=lambda topic: (
                (build_public_topic_recommendation(topic).get('recommendation_score') or 0),
                (build_public_topic_recommendation(topic).get('available') or 0),
                topic.created_at or datetime.min,
                topic.id or 0,
            ),
            reverse=True,
        )
        primary_topics = all_topics[:split_index]
        secondary_topics = all_topics[split_index:]
        first_available_topic = next((topic for topic in all_topics if (topic.filled or 0) < (topic.quota or 0)), None)
        announcement_count = len(list_announcements())
        trend_note_count = TrendNote.query.count()

        hero_title = (site_config.get('hero_title') or '').strip() or (activity.title if activity else '')
        hero_subtitle = (site_config.get('hero_subtitle') or '').strip() or (activity.description if activity else '')
        hero_badge = (site_config.get('hero_badge') or '').strip() or (activity.name if activity else '内容运营平台')

        return render_template(
            'index.html',
            activity=activity,
            primary_topics=primary_topics,
            secondary_topics=secondary_topics,
            first_available_topic=first_available_topic,
            announcement_count=announcement_count,
            trend_note_count=trend_note_count,
            site_config={
                **site_config,
                'hero_title': hero_title,
                'hero_subtitle': hero_subtitle,
                'hero_badge': hero_badge,
            },
            site_theme=site_theme,
        )

    @app.route('/announcements')
    def announcement_list():
        context = build_public_context()
        items = [serialize_announcement(item) for item in list_announcements()]
        return render_template(
            'public_collection.html',
            page_title='在线公告',
            page_heading='在线公告',
            page_description='查看当前正在生效的公告、通知和活动说明。',
            page_badge='公告中心',
            page_kind='announcement',
            items=items,
            empty_message='当前还没有生效中的公告。',
            **context,
        )

    @app.route('/trends')
    def trend_list():
        context = build_public_context()
        items = [
            serialize_public_trend(note)
            for note in TrendNote.query.order_by(TrendNote.created_at.desc(), TrendNote.id.desc()).limit(40).all()
        ]
        return render_template(
            'public_collection.html',
            page_title='热点速览',
            page_heading='热点速览',
            page_description='集中查看热点池里最近入库的热点和互动数据。',
            page_badge='热点池',
            page_kind='trend',
            items=items,
            empty_message='热点池暂时为空，可以稍后再看。',
            **context,
        )

    @app.route('/liver-science')
    def liver_science():
        context = build_public_context()
        dataset = build_liver_science_dataset()

        return render_template(
            'liver_science_hub.html',
            page_title='肝健康IP中心',
            page_heading='肝健康IP中心',
            page_description='这里把适合做肝健康个人 IP 的爆款案例、表达模板、长期知识库和栏目规划集中放在一起，帮助用户找到适合自己的方向，稳定输出内容。',
            page_badge='肝健康IP菜单',
            science_items=[serialize_public_corpus(item) for item in dataset['science_entries']],
            template_items=[serialize_public_corpus(item) for item in dataset['template_entries']],
            trend_items=[serialize_science_trend(item) for item in dataset['science_trends']],
            recent_auto_templates=dataset['recent_auto_templates'],
            lane_overview_rows=dataset['lane_overview_rows'],
            trend_groups=dataset['trend_groups'],
            template_groups=dataset['template_groups'],
            column_plans=dataset['column_plans'],
            top_keywords=dataset['top_keywords'],
            ip_lanes=LIVER_SCIENCE_IP_LANES,
            persona_lanes=LIVER_SCIENCE_PERSONA_LANES,
            ip_goal_options=LIVER_IP_GOAL_OPTIONS,
            ip_background_options=LIVER_IP_BACKGROUND_OPTIONS,
            ip_direction_options=LIVER_IP_DIRECTION_OPTIONS,
            **context,
        )

    @app.route('/hot-topics')
    def hot_topics():
        context = build_public_context()
        items = HotTopicEntry.query.filter_by(status='active').order_by(
            HotTopicEntry.hot_score.desc(),
            HotTopicEntry.updated_at.desc(),
            HotTopicEntry.id.desc(),
        ).limit(40).all()
        return render_template(
            'hot_topics_hub.html',
            page_title='热搜话题',
            page_heading='热搜话题',
            page_description='这里展示已经确认过、适合蹭热点的内容方向。不是只告诉你热搜词，而是会告诉你怎么蹭、适合谁写、怎么融合成肝健康IP内容。',
            page_badge='热搜与热点菜单',
            items=[serialize_public_hot_topic(item) for item in items],
            **context,
        )

    @app.route('/api/liver-ip/plan', methods=['POST'])
    def liver_ip_agent_plan():
        payload = request.json or {}
        result = build_liver_ip_agent_plan(payload)
        profile_key = (payload.get('profile_key') or '').strip()
        if result.get('success'):
            record = save_liver_ip_profile_plan(profile_key, payload, result)
            db.session.commit()
            result['profile_key'] = record.profile_key
            result['saved_profile'] = serialize_liver_ip_profile_plan(record)
        return jsonify(result)

    @app.route('/api/liver-ip/profile')
    def liver_ip_agent_profile():
        profile_key = (request.args.get('profile_key') or '').strip()
        if not profile_key:
            return jsonify({'success': False, 'message': '缺少 profile_key'})
        record = LiverIpProfilePlan.query.filter_by(profile_key=profile_key).first()
        if not record:
            return jsonify({'success': False, 'message': '未找到已保存的IP规划'})
        return jsonify({
            'success': True,
            'profile': serialize_liver_ip_profile_plan(record),
        })

    @app.route('/image-library')
    def public_image_library():
        context = build_public_context()
        base_query = AssetLibrary.query.filter_by(status='active').filter(
            AssetLibrary.preview_url.isnot(None),
            AssetLibrary.preview_url != '',
        )
        items = base_query.filter_by(pool_status='formal').order_by(
            AssetLibrary.created_at.desc(),
            AssetLibrary.id.desc(),
        ).limit(60).all()
        visibility_note = '当前展示正式图片库内容。'
        if not items:
            items = base_query.filter(AssetLibrary.pool_status != 'archived').order_by(
                AssetLibrary.created_at.desc(),
                AssetLibrary.id.desc(),
            ).limit(60).all()
            visibility_note = '当前正式图片库为空，已临时展示非归档图片内容。'

        return render_template(
            'public_image_library.html',
            page_title='图片库',
            page_heading='图片库',
            page_description='集中查看可直接参考或下载的图片素材。',
            page_badge='内容素材',
            items=[serialize_public_asset(item) for item in items],
            visibility_note=visibility_note,
            **context,
        )

    @app.route('/api/public-assets')
    def public_assets_api():
        library_type = (request.args.get('library_type') or '').strip()
        library_types_raw = (request.args.get('library_types') or '').strip()
        keyword = (request.args.get('keyword') or '').strip()
        limit = min(max(int(request.args.get('limit') or 12), 1), 60)

        query = AssetLibrary.query.filter_by(status='active').filter(
            AssetLibrary.preview_url.isnot(None),
            AssetLibrary.preview_url != '',
            AssetLibrary.pool_status != 'archived',
        )
        if library_types_raw:
            library_types = [item.strip() for item in library_types_raw.split(',') if item.strip()]
            if len(library_types) == 1:
                query = query.filter_by(library_type=library_types[0])
            elif library_types:
                query = query.filter(AssetLibrary.library_type.in_(library_types))
        elif library_type:
            query = query.filter_by(library_type=library_type)
        if keyword:
            for token in [item.strip() for item in keyword.replace('，', ',').replace('、', ',').split(',') if item.strip()][:5]:
                query = query.filter(
                    (AssetLibrary.title.contains(token)) |
                    (AssetLibrary.subtitle.contains(token)) |
                    (AssetLibrary.tags.contains(token)) |
                    (AssetLibrary.product_name.contains(token)) |
                    (AssetLibrary.product_indication.contains(token))
                )
        items = query.order_by(AssetLibrary.created_at.desc(), AssetLibrary.id.desc()).all()
        serialized_items = [serialize_public_asset(item) for item in items]
        usage_rank_map = {'cover': 3, 'inner': 2, 'general': 1}
        serialized_items.sort(
            key=lambda item: (
                100000 if item.get('library_type_key') == 'generated' else 0,
                (item.get('usable_score') or 0) * 10,
                usage_rank_map.get(item.get('recommended_usage') or '', 0),
                item.get('created_at') or '',
            ),
            reverse=True,
        )
        return jsonify({
            'success': True,
            'items': serialized_items[:limit],
        })

    @app.route('/topic/<int:topic_id>')
    def topic_detail(topic_id):
        topic = Topic.query.get_or_404(topic_id)
        return render_template(
            'topic_detail.html',
            topic=topic,
            topic_recommendation=build_public_topic_recommendation(topic),
            **build_public_context(),
        )

    @app.route('/register_success/<int:reg_id>')
    def register_success(reg_id):
        reg = Registration.query.get_or_404(reg_id)
        return render_template(
            'register_success.html',
            registration=reg,
            tracking_summary=build_registration_tracking_summary(reg),
            asset_style_types=asset_style_type_options(),
            copy_skill_options=copy_skill_options(),
            title_skill_options=title_skill_options(),
            image_skill_options=image_skill_options(),
            image_skill_presets=image_skill_presets(),
            saved_strategy=serialize_submission_strategy(reg.submission) if reg.submission else {},
            strategy_recommendation=build_strategy_recommendation_payload(reg),
            task_agent_brief=build_task_agent_brief_payload(reg),
            **build_public_context(),
        )

    @app.route('/api/asset_style_recommendations', methods=['POST'])
    def public_asset_style_recommendations():
        payload = request.json or {}
        return jsonify(build_asset_style_recommendation_payload(payload))

    @app.route('/api/strategy_recommendations/<int:reg_id>')
    def public_strategy_recommendations(reg_id):
        reg = Registration.query.get_or_404(reg_id)
        return jsonify(build_strategy_recommendation_payload(reg))

    @app.route('/api/task_agent_brief/<int:reg_id>')
    def public_task_agent_brief(reg_id):
        reg = Registration.query.get_or_404(reg_id)
        return jsonify(build_task_agent_brief_payload(reg))

    @app.route('/api/strategy_selection', methods=['POST'])
    def save_strategy_selection():
        data = request.json or {}
        reg = Registration.query.get(data.get('registration_id'))
        if not reg:
            return jsonify({'success': False, 'message': '报名信息不存在'})

        submission = Submission.query.filter_by(registration_id=reg.id).first()
        if not submission:
            submission = Submission(registration_id=reg.id)
            db.session.add(submission)
            db.session.flush()

        strategy = apply_submission_strategy_snapshot(submission, data, registration=reg)
        db.session.commit()
        return jsonify({
            'success': True,
            'stored': True,
            'message': '任务策略已保存',
            'strategy': strategy,
        })

    @app.route('/my_registration', methods=['GET', 'POST'])
    def my_registration():
        reg_id = request.args.get('reg_id')
        if reg_id:
            reg = Registration.query.get(int(reg_id))
            if reg:
                return render_my_registration_page(registrations=[reg])

        if request.method == 'POST':
            group_num = request.form.get('group_num')
            name = request.form.get('name')
            regs = Registration.query.filter_by(group_num=group_num, name=name).all()
            if regs:
                return render_my_registration_page(registrations=regs)
            return render_my_registration_page(error='未找到报名信息')

        return render_my_registration_page()

    @app.route('/api/topics/<int:activity_id>')
    def get_topics(activity_id):
        topics = Topic.query.filter_by(activity_id=activity_id).all()
        topics = sorted(
            topics,
            key=lambda topic: (
                (build_public_topic_recommendation(topic).get('recommendation_score') or 0),
                (build_public_topic_recommendation(topic).get('available') or 0),
                topic.created_at or datetime.min,
                topic.id or 0,
            ),
            reverse=True,
        )
        return jsonify([serialize_public_topic(topic) for topic in topics])

    @app.route('/api/profile_by_phone')
    def profile_by_phone():
        phone = (request.args.get('phone') or '').strip()
        if not phone:
            return jsonify({'success': False, 'message': '手机号不能为空'})

        reg = Registration.query.filter_by(phone=phone).order_by(Registration.created_at.desc()).first()
        if not reg:
            return jsonify({'success': True, 'found': False})

        return jsonify({
            'success': True,
            'found': True,
            'profile': {
                'name': reg.name or '',
                'xhs_account': reg.xhs_account or '',
                'group_num': reg.group_num or '',
                'xhs_profile_link': reg.submission.xhs_profile_link if reg.submission and reg.submission.xhs_profile_link else '',
            }
        })

    @app.route('/api/register', methods=['POST'])
    def register():
        data = request.json
        topic = Topic.query.get(data.get('topic_id'))

        if not topic:
            return jsonify({'success': False, 'message': '话题不存在'})
        if topic.filled >= topic.quota:
            return jsonify({'success': False, 'message': '名额已满'})

        existing = Registration.query.filter_by(
            topic_id=data.get('topic_id'),
            xhs_account=data.get('xhs_account')
        ).first()
        if existing:
            return jsonify({'success': False, 'message': '您已报名此话题'})

        reg = Registration(
            topic_id=data.get('topic_id'),
            group_num=data.get('group_num'),
            name=data.get('name'),
            phone=data.get('phone'),
            xhs_account=data.get('xhs_account')
        )
        db.session.add(reg)
        topic.filled += 1
        db.session.commit()

        return jsonify({'success': True, 'message': '报名成功', 'registration_id': reg.id})

    @app.route('/api/submit', methods=['POST'])
    def submit_data():
        data = request.json or {}
        reg = Registration.query.get(data.get('registration_id'))

        if not reg:
            return jsonify({'success': False, 'message': '报名信息不存在'})

        try:
            normalized = validate_required_platform_data(data)
        except ValueError as e:
            return jsonify({'success': False, 'message': str(e)})

        note_title = (data.get('note_title') or '').strip()
        note_content = (data.get('note_content') or '').strip()
        auto_type = auto_detect_content_type(f"{note_title} {note_content}", reg.topic.topic_name if reg and reg.topic else '')
        if note_title:
            normalized['note_title'] = note_title
        if note_content:
            normalized['note_content'] = note_content
        normalized['content_type'] = auto_type

        topic = reg.topic
        keywords = topic.keywords.split(',') if topic.keywords else []
        existing_submission = Submission.query.filter_by(registration_id=reg.id).first()
        xhs_for_check = normalized.get('xhs_link')
        if not xhs_for_check and existing_submission:
            xhs_for_check = existing_submission.xhs_link or ''
        keyword_check = any(k.strip() in (xhs_for_check or '') for k in keywords if k.strip())

        if existing_submission:
            for key, value in normalized.items():
                setattr(existing_submission, key, value)
            existing_submission.keyword_check = keyword_check
            existing_submission.created_at = datetime.now()
            submission = existing_submission
        else:
            submission = Submission(
                registration_id=reg.id,
                keyword_check=keyword_check,
                **normalized
            )
            db.session.add(submission)
            db.session.flush()

        if data.get('selected_title') or data.get('selected_title_skill') or data.get('strategy_payload'):
            apply_submission_strategy_snapshot(submission, data, registration=reg)

        tracking_summary = sync_tracking_from_submission(reg, submission, data)
        reg.status = 'submitted'
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '提交成功，已开启小红书账号持续跟踪' if tracking_summary.get('enabled') else '提交成功',
            'tracking': tracking_summary,
        })

    @app.route('/api/update_data', methods=['POST'])
    def update_data():
        data = request.json or {}
        reg = Registration.query.get(data.get('registration_id'))

        if not reg:
            return jsonify({'success': False, 'message': '报名信息不存在'})

        submission = Submission.query.filter_by(registration_id=reg.id).first()
        if not submission:
            submission = Submission(registration_id=reg.id)
            db.session.add(submission)

        try:
            partial = validate_partial_platform_data(data, require_at_least_one_link=False)
        except ValueError as e:
            return jsonify({'success': False, 'message': str(e)})

        for key, value in partial.items():
            setattr(submission, key, value)

        note_title = (data.get('note_title') or '').strip()
        note_content = (data.get('note_content') or '').strip()
        if note_title:
            submission.note_title = note_title
        if note_content:
            submission.note_content = note_content
        if note_title or note_content or (submission.note_title or submission.note_content):
            submission.content_type = auto_detect_content_type(
                f"{submission.note_title or ''} {submission.note_content or ''}",
                reg.topic.topic_name if reg and reg.topic else '',
            )

        if data.get('selected_title') or data.get('selected_title_skill') or data.get('strategy_payload'):
            apply_submission_strategy_snapshot(submission, data, registration=reg)

        db.session.flush()
        tracking_summary = sync_tracking_from_submission(reg, submission, data)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '数据更新成功，账号持续跟踪已同步' if tracking_summary.get('enabled') else '数据更新成功',
            'tracking': tracking_summary,
        })
