import os

from models import Settings


AUTOMATION_RUNTIME_CONFIG_DEFAULTS = {
    'hotword_source_platform': '小红书',
    'hotword_source_template': 'generic_lines',
    'hotword_source_channel': 'Worker骨架',
    'hotword_keyword_limit': 10,
    'hotword_fetch_mode': 'auto',
    'hotword_api_url': '',
    'hotword_api_method': 'GET',
    'hotword_api_headers_json': '',
    'hotword_api_query_json': '',
    'hotword_api_body_json': '',
    'hotword_result_path': '',
    'hotword_keyword_param': 'keyword',
    'hotword_timeout_seconds': 30,
    'hotword_auto_generate_topic_ideas': False,
    'hotword_auto_generate_topic_count': 20,
    'hotword_auto_generate_topic_activity_id': 0,
    'hotword_auto_generate_topic_quota': 30,
    'creator_sync_source_channel': 'Crawler服务',
    'creator_sync_fetch_mode': 'auto',
    'creator_sync_api_url': '',
    'creator_sync_api_method': 'POST',
    'creator_sync_api_headers_json': '',
    'creator_sync_api_query_json': '',
    'creator_sync_api_body_json': '',
    'creator_sync_result_path': '',
    'creator_sync_timeout_seconds': 60,
    'creator_sync_batch_limit': 20,
    'image_provider': 'svg_fallback',
    'image_api_url': '',
    'image_api_base': '',
    'image_model': '',
    'image_size': '1024x1536',
    'image_timeout_seconds': 90,
    'image_style_preset': '小红书图文',
    'image_default_style_type': 'medical_science',
    'image_optimize_prompt_mode': 'standard',
    'image_prompt_suffix': '',
}

IMAGE_PROVIDER_OPTIONS = [
    {'key': 'svg_fallback', 'label': 'SVG兜底'},
    {'key': 'volcengine_ark', 'label': '火山方舟兼容模式'},
    {'key': 'volcengine_las', 'label': '火山 LAS 接口'},
    {'key': 'openai', 'label': 'OpenAI'},
    {'key': 'openai_compatible', 'label': 'OpenAI兼容接口'},
    {'key': 'generic_json', 'label': '通用JSON接口'},
]

IMAGE_PROVIDER_PRESETS = [
    {
        'key': 'svg_fallback_default',
        'label': 'SVG 兜底',
        'description': '不依赖外部图片接口，适合无 API 时演示联调。',
        'config': {
            'image_provider': 'svg_fallback',
            'image_api_base': '',
            'image_api_url': '',
            'image_model': '',
            'image_size': '1024x1536',
        },
    },
    {
        'key': 'volcengine_ark_default',
        'label': '火山方舟默认',
        'description': '适合火山方舟兼容 OpenAI 图片接口，默认 API Base 与模型占位已带上。',
        'config': {
            'image_provider': 'volcengine_ark',
            'image_api_base': 'https://ark.cn-beijing.volces.com/api/v3',
            'image_api_url': '',
            'image_model': 'doubao-seededit-3-0-i2i-250628',
            'image_size': '1024x1536',
        },
    },
    {
        'key': 'volcengine_las_default',
        'label': '火山 LAS 默认',
        'description': '适合火山 LAS 图片生成接口，默认 API Base 与 seedream 模型占位已带上。',
        'config': {
            'image_provider': 'volcengine_las',
            'image_api_base': 'https://operator.las.cn-beijing.volces.com/api/v1',
            'image_api_url': '',
            'image_model': 'doubao-seedream-5-0-lite-260128',
            'image_size': '1024x1536',
        },
    },
    {
        'key': 'openai_compatible_default',
        'label': 'OpenAI 兼容默认',
        'description': '适合任何兼容 OpenAI image generation 的网关或第三方接口。',
        'config': {
            'image_provider': 'openai_compatible',
            'image_api_base': '',
            'image_api_url': '',
            'image_model': 'gpt-image-1',
            'image_size': '1024x1536',
        },
    },
    {
        'key': 'generic_json_default',
        'label': '通用 JSON 默认',
        'description': '适合自定义图片接口，只要返回 data/images/results 结构即可。',
        'config': {
            'image_provider': 'generic_json',
            'image_api_base': '',
            'image_api_url': '',
            'image_model': 'image-default',
            'image_size': '1024x1536',
        },
    },
]

ASSET_STYLE_TYPE_DEFINITIONS = [
    {
        'key': 'medical_science',
        'label': '医学科普型',
        'description': '适合封面警示、症状总览、检查解读、器官科普',
        'asset_type': '医学科普图',
        'default_size': '1536x2048',
        'prompt_suffix': '整体是小红书医学科普封面气质，标题强、结论清楚、信息图层级明确。',
        'default_bullets': ['问题先抛出来', '解释指标或误区', '最后给管理建议'],
        'accent': '#ff7a59',
        'bg': '#fff4ee',
        'layout_hint': '顶部超大标题区，中部主体医学插画，下方结论条或标签区',
        'visual_hint': '半写实医学手绘插画结合轻信息图风格，专业可信但不生硬',
        'reference_hint': '参考小红书医疗健康警示封面、症状总览图、检查解读图的感觉',
        'text_policy': '优先保留大标题和少量短标签；如果模型文字能力一般，就预留标题区和标签框，避免大段乱码中文',
        'avoid_hint': '不要医院广告海报感，不要品牌露出，不要暗黑恐怖，不要赛博霓虹，不要复杂摄影背景',
    },
    {
        'key': 'poster',
        'label': '大字报',
        'description': '适合强标题、情绪冲击、核心结论型封面',
        'asset_type': '大字报',
        'default_size': '1536x2048',
        'prompt_suffix': '强调一个主标题，视觉冲击强，适合封面传播，信息点精简。',
        'default_bullets': ['一句大结论', '一个关键提醒', '一条行动建议'],
        'accent': '#ef4e45',
        'bg': '#fff2f0',
    },
    {
        'key': 'checklist',
        'label': '清单',
        'description': '适合步骤、提醒、准备事项和执行动作',
        'asset_type': '清单',
        'default_size': '1536x2048',
        'prompt_suffix': '清单结构，条目感强，适合打勾式阅读体验。',
        'default_bullets': ['先做什么', '中间检查什么', '最后复盘什么'],
        'accent': '#2d8f5a',
        'bg': '#f1fbf5',
    },
    {
        'key': 'memo',
        'label': '备忘录',
        'description': '适合提醒、注意事项、门诊问答记录',
        'asset_type': '备忘录',
        'default_size': '1536x2048',
        'prompt_suffix': '像随手记下来的重点备忘，便签感、记录感强，但整体要整洁。',
        'default_bullets': ['今天先记住', '这类情况要留意', '复查前别忘了'],
        'accent': '#5c6ac4',
        'bg': '#f3f4ff',
    },
    {
        'key': 'knowledge_card',
        'label': '知识卡片型',
        'description': '适合结构图、机制图、对比卡、收藏型内页',
        'asset_type': '知识卡片',
        'default_size': '1536x2048',
        'prompt_suffix': '整体像小红书医学知识卡片内页，结构图完整，适合收藏转发。',
        'default_bullets': ['一个知识点', '一个误区', '一个建议'],
        'accent': '#4c91ff',
        'bg': '#eef5ff',
        'layout_hint': '白底或米白底卡片，四周细边框，顶部大标题，中部核心结构图，周围箭头标签和局部放大，下方总结信息条',
        'visual_hint': '医学结构插画、机制流程图、局部放大和标签说明并存，整体干净、整齐、易收藏',
        'reference_hint': '参考小红书医学知识卡片、机制图、对比讲解页的感觉',
        'text_policy': '适合短标题、短标签、编号提示；尽量不要密集长段落，优先给排版留出信息框区域',
        'avoid_hint': '不要纯海报感，不要只有一个主体没有信息层级，不要花哨背景，不要写实商业广告感',
    },
    {
        'key': 'myth_compare',
        'label': '误区对照图',
        'description': '适合左右对照、真伪辨析和避坑内容',
        'asset_type': '误区对照图',
        'default_size': '1536x2048',
        'prompt_suffix': '左右对照结构明显，适合“误区 vs 正解”表达。',
        'default_bullets': ['常见误区', '正确理解', '实际怎么做'],
        'accent': '#d96570',
        'bg': '#fff2f5',
    },
    {
        'key': 'flowchart',
        'label': '流程图',
        'description': '适合检查流程、复查流程、就诊步骤',
        'asset_type': '流程图',
        'default_size': '1536x2048',
        'prompt_suffix': '流程步骤清晰，方向性强，适合路线图阅读方式。',
        'default_bullets': ['第一步', '第二步', '第三步'],
        'accent': '#f2a43c',
        'bg': '#fff8ea',
    },
]

VOLCENGINE_MODEL_OPTIONS = [
    {'key': 'doubao-seedream-5-0-lite-260128', 'label': 'Seedream 5.0 lite', 'provider': 'volcengine_las'},
    {'key': 'doubao-seedream-5-0-260128', 'label': 'Seedream 5.0', 'provider': 'volcengine_las'},
    {'key': 'doubao-seedream-4-5-251128', 'label': 'Seedream 4.5', 'provider': 'volcengine_las'},
    {'key': 'doubao-seedream-4-0-250828', 'label': 'Seedream 4.0', 'provider': 'volcengine_las'},
    {'key': 'doubao-seededit-3-0-i2i-250628', 'label': 'SeedEdit 3.0', 'provider': 'volcengine_ark'},
]

MEDICAL_SCIENCE_LAYOUT_VARIANTS = {
    'impact_compare': '采用左右对照信息图版式：左侧是危险状态或错误行为，右侧是健康状态或正确做法，中间可用箭头或对照符号强化反差。',
    'symptom_warning': '采用警示科普版式：主标题强提醒，中部为人体或器官示意图，四周分布症状标签、风险信号和结论提示。',
    'device_explainer': '采用检查设备解读版式：主体是设备或检查场景，旁边搭配成像原理、适用场景、优缺点、注意事项等信息块。',
    'organ_explainer': '采用器官科普版式：一个核心器官或人体系统作为主体，配合局部放大、箭头标签、误区提示和管理建议。',
}

KNOWLEDGE_CARD_LAYOUT_VARIANTS = {
    'comparison_card': '采用对比知识卡版式：左中右或上下分区清楚，适合表达外表正常 vs 体内异常、误区 vs 真相、不同状态对照。',
    'mechanism_cycle': '采用机制流程卡版式：中心器官或核心结论居中，周围用环形箭头、因果路径和编号标签说明机制。',
    'body_map': '采用全身影响总览卡版式：人体轮廓或核心器官置中，四周分布系统影响、风险结果和重点提示。',
    'knowledge_breakdown': '采用结构拆解卡版式：顶部标题，中部核心结构图或剖面图，旁边补充定义、风险、指标和行动建议。',
}

STYLE_REFERENCE_SIGNATURES = {
    'medical_science': {
        'core_style': '贴近你提供的“小红书医学科普封面”样例：顶部超大黑色中文标题，必要时加一个小徽标或警示角标，中部是主体信息图，底部有一条总结式横幅或结论栏。',
        'composition': '常见构图是左右对比、人体总览、器官+局部放大、设备+说明块，阅读路径要非常直接，一眼看懂重点。',
        'palette': '颜色采用白底、浅蓝绿、浅暖灰作为主色，橙红和黄色只做警示强调，不要高饱和商业海报色。',
        'illustration': '插画是医学手绘科普风，器官、人体、检查设备要准确，带一点柔和上色和线稿质感，像高质量健康科普账号配图。',
        'annotation': '画面里要有短标签框、箭头、图标、对勾叉号、提示小框，但保持整洁，不要挤成论文海报。',
        'footer': '底部适合放一句强结论、一条风险提醒或一条行动建议，形成封面收口。',
        'avoid': '不要欧美扁平插画感，不要时尚杂志排版，不要赛博未来风，不要纯摄影拼贴。',
    },
    'knowledge_card': {
        'core_style': '贴近你提供的“医学知识卡片”样例：白底或米白底，四周细边框，顶部超大黑标题，副标题可用橙色强调，中部是完整结构图或机制图。',
        'composition': '常见构图是器官剖面图、机制循环图、左右对比图、人体影响总览图，周围配箭头、编号、标签框、局部放大图。',
        'palette': '颜色采用米白、浅橙、肉粉、浅蓝、浅绿、咖色线稿，整体温和、清晰、像可收藏的医学笔记卡片。',
        'illustration': '插画应当偏医学手绘和知识图谱结合，不是极简图标，也不是过度写实的商业渲染。',
        'annotation': '标签一定要短、准、整齐，信息块彼此分明，像小红书里高收藏的医学讲解页。',
        'footer': '底部留一条灰白或米色总结区，适合放结论、定义、检查建议或提醒。',
        'avoid': '不要只有一个器官孤零零摆在中间，不要背景花里胡哨，不要广告感文案排版。',
    },
}


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_json_value(raw_value, default):
    if not raw_value:
        return default
    try:
        parsed = __import__('json').loads(raw_value)
    except Exception:
        return default
    return parsed if isinstance(parsed, type(default)) else default


def _automation_runtime_config():
    config = dict(AUTOMATION_RUNTIME_CONFIG_DEFAULTS)
    try:
        setting = Settings.query.filter_by(key='automation_runtime_config').first()
        parsed = _load_json_value(setting.value if setting else '', {})
        if isinstance(parsed, dict):
            for key in config.keys():
                value = parsed.get(key)
                if value in [None, '']:
                    continue
                config[key] = value
    except Exception:
        pass
    return config


def _hotword_runtime_settings():
    config = dict(_automation_runtime_config())
    env_overrides = {
        'hotword_fetch_mode': (os.environ.get('HOTWORD_FETCH_MODE') or '').strip(),
        'hotword_api_url': (os.environ.get('HOTWORD_API_URL') or '').strip(),
        'hotword_api_method': (os.environ.get('HOTWORD_API_METHOD') or '').strip(),
        'hotword_api_headers_json': (os.environ.get('HOTWORD_API_HEADERS_JSON') or '').strip(),
        'hotword_api_query_json': (os.environ.get('HOTWORD_API_QUERY_JSON') or '').strip(),
        'hotword_api_body_json': (os.environ.get('HOTWORD_API_BODY_JSON') or '').strip(),
        'hotword_result_path': (os.environ.get('HOTWORD_RESULT_PATH') or '').strip(),
        'hotword_keyword_param': (os.environ.get('HOTWORD_KEYWORD_PARAM') or '').strip(),
        'hotword_auto_generate_topic_ideas': (os.environ.get('HOTWORD_AUTO_GENERATE_TOPIC_IDEAS') or '').strip(),
    }
    timeout_value = (os.environ.get('HOTWORD_TIMEOUT_SECONDS') or '').strip()
    if timeout_value:
        env_overrides['hotword_timeout_seconds'] = _safe_int(timeout_value, config.get('hotword_timeout_seconds', 30))
    auto_generate_count = (os.environ.get('HOTWORD_AUTO_GENERATE_TOPIC_COUNT') or '').strip()
    if auto_generate_count:
        env_overrides['hotword_auto_generate_topic_count'] = _safe_int(auto_generate_count, config.get('hotword_auto_generate_topic_count', 20))
    auto_generate_activity = (os.environ.get('HOTWORD_AUTO_GENERATE_TOPIC_ACTIVITY_ID') or '').strip()
    if auto_generate_activity:
        env_overrides['hotword_auto_generate_topic_activity_id'] = _safe_int(auto_generate_activity, config.get('hotword_auto_generate_topic_activity_id', 0))
    auto_generate_quota = (os.environ.get('HOTWORD_AUTO_GENERATE_TOPIC_QUOTA') or '').strip()
    if auto_generate_quota:
        env_overrides['hotword_auto_generate_topic_quota'] = _safe_int(auto_generate_quota, config.get('hotword_auto_generate_topic_quota', 30))

    for key, value in env_overrides.items():
        if value not in [None, '']:
            config[key] = value
    config['hotword_timeout_seconds'] = min(max(_safe_int(config.get('hotword_timeout_seconds'), 30), 5), 120)
    config['hotword_fetch_mode'] = (config.get('hotword_fetch_mode') or 'auto').strip().lower() or 'auto'
    config['hotword_api_method'] = (config.get('hotword_api_method') or 'GET').strip().upper() or 'GET'
    config['hotword_keyword_param'] = (config.get('hotword_keyword_param') or 'keyword').strip() or 'keyword'
    config['hotword_auto_generate_topic_ideas'] = str(config.get('hotword_auto_generate_topic_ideas') or '').strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
    config['hotword_auto_generate_topic_count'] = min(max(_safe_int(config.get('hotword_auto_generate_topic_count'), 20), 1), 120)
    config['hotword_auto_generate_topic_activity_id'] = max(_safe_int(config.get('hotword_auto_generate_topic_activity_id'), 0), 0)
    config['hotword_auto_generate_topic_quota'] = min(max(_safe_int(config.get('hotword_auto_generate_topic_quota'), 30), 1), 300)
    return config


def _resolved_hotword_mode(runtime_settings=None):
    runtime_settings = runtime_settings or _hotword_runtime_settings()
    configured_mode = (runtime_settings.get('hotword_fetch_mode') or 'auto').strip().lower() or 'auto'
    api_url = (runtime_settings.get('hotword_api_url') or '').strip()
    if configured_mode == 'auto':
        return 'remote' if api_url else 'skeleton'
    return configured_mode if configured_mode in {'remote', 'skeleton'} else 'skeleton'


def _creator_sync_runtime_settings():
    config = dict(_automation_runtime_config())
    env_overrides = {
        'creator_sync_source_channel': (os.environ.get('CREATOR_SYNC_SOURCE_CHANNEL') or '').strip(),
        'creator_sync_fetch_mode': (os.environ.get('CREATOR_SYNC_FETCH_MODE') or '').strip(),
        'creator_sync_api_url': (os.environ.get('CREATOR_SYNC_API_URL') or '').strip(),
        'creator_sync_api_method': (os.environ.get('CREATOR_SYNC_API_METHOD') or '').strip(),
        'creator_sync_api_headers_json': (os.environ.get('CREATOR_SYNC_API_HEADERS_JSON') or '').strip(),
        'creator_sync_api_query_json': (os.environ.get('CREATOR_SYNC_API_QUERY_JSON') or '').strip(),
        'creator_sync_api_body_json': (os.environ.get('CREATOR_SYNC_API_BODY_JSON') or '').strip(),
        'creator_sync_result_path': (os.environ.get('CREATOR_SYNC_RESULT_PATH') or '').strip(),
    }
    timeout_value = (os.environ.get('CREATOR_SYNC_TIMEOUT_SECONDS') or '').strip()
    if timeout_value:
        env_overrides['creator_sync_timeout_seconds'] = _safe_int(timeout_value, config.get('creator_sync_timeout_seconds', 60))
    batch_limit_value = (os.environ.get('CREATOR_SYNC_BATCH_LIMIT') or '').strip()
    if batch_limit_value:
        env_overrides['creator_sync_batch_limit'] = _safe_int(batch_limit_value, config.get('creator_sync_batch_limit', 20))

    for key, value in env_overrides.items():
        if value not in [None, '']:
            config[key] = value
    config['creator_sync_source_channel'] = (config.get('creator_sync_source_channel') or 'Crawler服务').strip() or 'Crawler服务'
    config['creator_sync_fetch_mode'] = (config.get('creator_sync_fetch_mode') or 'auto').strip().lower() or 'auto'
    config['creator_sync_api_method'] = (config.get('creator_sync_api_method') or 'POST').strip().upper() or 'POST'
    config['creator_sync_timeout_seconds'] = min(max(_safe_int(config.get('creator_sync_timeout_seconds'), 60), 5), 300)
    config['creator_sync_batch_limit'] = min(max(_safe_int(config.get('creator_sync_batch_limit'), 20), 1), 200)
    return config


def _resolved_creator_sync_mode(runtime_settings=None):
    runtime_settings = runtime_settings or _creator_sync_runtime_settings()
    configured_mode = (runtime_settings.get('creator_sync_fetch_mode') or 'auto').strip().lower() or 'auto'
    api_url = (runtime_settings.get('creator_sync_api_url') or '').strip()
    if configured_mode == 'auto':
        return 'remote' if api_url else 'disabled'
    return configured_mode if configured_mode in {'remote', 'disabled'} else 'disabled'


def _image_provider_options():
    return [dict(item) for item in IMAGE_PROVIDER_OPTIONS]


def _image_provider_presets():
    return [dict(item) for item in IMAGE_PROVIDER_PRESETS]


def _asset_style_type_options():
    return [dict(item) for item in ASSET_STYLE_TYPE_DEFINITIONS]


def _asset_style_meta(style_value):
    raw = (style_value or '').strip()
    for item in ASSET_STYLE_TYPE_DEFINITIONS:
        if raw == item['key'] or raw == item['label']:
            return dict(item)
    default_item = ASSET_STYLE_TYPE_DEFINITIONS[0]
    fallback = dict(default_item)
    if raw:
        fallback['label'] = raw
        fallback['asset_type'] = raw
    return fallback


def _image_model_options(provider=''):
    current_provider = (provider or '').strip()
    if current_provider in {'volcengine_ark', 'volcengine_las'}:
        return [dict(item) for item in VOLCENGINE_MODEL_OPTIONS]
    return []


def _image_provider_capabilities():
    runtime_config = _automation_runtime_config()
    provider = (os.environ.get('ASSET_IMAGE_PROVIDER') or str(runtime_config.get('image_provider') or 'svg_fallback')).strip() or 'svg_fallback'
    api_base = (os.environ.get('ASSET_IMAGE_API_BASE') or str(runtime_config.get('image_api_base') or '')).strip()
    if provider == 'volcengine_ark' and not api_base:
        api_base = 'https://ark.cn-beijing.volces.com/api/v3'
    if provider == 'volcengine_las' and not api_base:
        api_base = 'https://operator.las.cn-beijing.volces.com/api/v1'
    api_url = (os.environ.get('ASSET_IMAGE_API_URL') or str(runtime_config.get('image_api_url') or '')).strip()
    if not api_url and api_base:
        api_url = api_base.rstrip('/') + '/images/generations'
    api_key = (
        os.environ.get('ASSET_IMAGE_API_KEY')
        or os.environ.get('ARK_API_KEY')
        or os.environ.get('LAS_API_KEY')
        or ''
    ).strip()
    model_name = (os.environ.get('ASSET_IMAGE_MODEL') or str(runtime_config.get('image_model') or '')).strip()
    if not model_name and provider in {'volcengine_ark', 'volcengine_las'}:
        model_name = 'doubao-seedream-5-0-lite-260128'
    image_size = (os.environ.get('ASSET_IMAGE_SIZE') or str(runtime_config.get('image_size') or '1024x1536')).strip()
    timeout_seconds = min(max(_safe_int(runtime_config.get('image_timeout_seconds'), 90), 10), 300)
    configured = bool(api_url and api_key)
    return {
        'image_provider_configured': configured,
        'image_provider_name': provider,
        'image_provider_api_base': api_base,
        'image_provider_api_url': api_url,
        'image_provider_model': model_name,
        'image_provider_size': image_size,
        'image_timeout_seconds': timeout_seconds,
        'image_style_preset': str(runtime_config.get('image_style_preset') or '小红书图文'),
        'image_default_style_type': str(runtime_config.get('image_default_style_type') or 'medical_science'),
        'image_optimize_prompt_mode': str(runtime_config.get('image_optimize_prompt_mode') or 'standard'),
        'image_prompt_suffix': str(runtime_config.get('image_prompt_suffix') or ''),
        'api_key_configured': bool(api_key),
        'fallback_mode': not configured or provider == 'svg_fallback',
        'provider_options': _image_provider_options(),
        'model_options': _image_model_options(provider),
        'style_type_options': _asset_style_type_options(),
    }
