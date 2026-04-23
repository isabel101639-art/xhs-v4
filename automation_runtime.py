import os

from models import Settings


AUTOMATION_RUNTIME_CONFIG_DEFAULTS = {
    'hotword_source_platform': '小红书',
    'hotword_source_template': 'generic_lines',
    'hotword_source_channel': 'Worker骨架',
    'hotword_keyword_limit': 10,
    'hotword_scope_preset': 'liver_comorbidity',
    'hotword_time_window': '30d',
    'hotword_date_from': '',
    'hotword_date_to': '',
    'hotword_fetch_mode': 'auto',
    'hotword_api_url': '',
    'hotword_api_method': 'GET',
    'hotword_api_headers_json': '',
    'hotword_api_query_json': '',
    'hotword_api_body_json': '',
    'hotword_result_path': '',
    'hotword_keyword_param': 'keyword',
    'hotword_timeout_seconds': 30,
    'hotword_trend_type': 'note_search',
    'hotword_page_size': 20,
    'hotword_max_related_queries': 20,
    'hotword_auto_generate_topic_ideas': False,
    'hotword_auto_generate_topic_count': 20,
    'hotword_auto_generate_topic_activity_id': 0,
    'hotword_auto_generate_topic_quota': 30,
    'hotword_auto_convert_corpus_templates': False,
    'hotword_auto_convert_corpus_limit': 10,
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
    'creator_sync_current_month_only': True,
    'creator_sync_date_from': '',
    'creator_sync_date_to': '',
    'creator_sync_max_posts_per_account': 60,
    'copywriter_api_url': '',
    'copywriter_model': '',
    'copywriter_backup_api_url': '',
    'copywriter_backup_model': '',
    'copywriter_third_api_url': '',
    'copywriter_third_model': '',
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
        'key': 'openai_default',
        'label': 'OpenAI 官方默认',
        'description': '适合直接调用 OpenAI 官方图片接口，默认带上官方 API Base 和通用模型占位。',
        'config': {
            'image_provider': 'openai',
            'image_api_base': 'https://api.openai.com/v1',
            'image_api_url': '',
            'image_model': 'gpt-image-1',
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

PRODUCT_CATEGORY_OPTIONS = [
    {'key': 'medicine', 'label': '药品'},
    {'key': 'device', 'label': '器械'},
]

PRODUCT_VISUAL_ROLE_OPTIONS = [
    {'key': 'hero', 'label': '主视觉图'},
    {'key': 'standard_pack', 'label': '标准包装图'},
    {'key': 'detail', 'label': '细节图 / 剂型图'},
    {'key': 'scene', 'label': '场景图'},
    {'key': 'instruction', 'label': '背面说明图'},
    {'key': 'device_ui', 'label': '设备界面图'},
    {'key': 'family_lineup', 'label': '产品家族图'},
    {'key': 'reference_style', 'label': '风格参考图'},
]

PRODUCT_PROFILE_DEFINITIONS = [
    {
        'key': 'fibroscan_handy',
        'label': 'FibroScan Handy',
        'product_category': 'device',
        'product_name': 'FibroScan Handy',
        'product_indication': '肝脏无创监测 / 肝弹检测',
        'default_visual_role': 'hero',
        'default_tags': ['FibroScan', '福波看', '肝弹', '器械'],
    },
    {
        'key': 'fibroscan_pro',
        'label': 'FibroScan PRO',
        'product_category': 'device',
        'product_name': 'FibroScan PRO',
        'product_indication': '肝脏无创监测 / 肝弹检测',
        'default_visual_role': 'hero',
        'default_tags': ['FibroScan', '福波看', '肝弹', '器械'],
    },
    {
        'key': 'fibroscan_630',
        'label': 'FibroScan 630',
        'product_category': 'device',
        'product_name': 'FibroScan 630',
        'product_indication': '肝脏无创监测 / 肝弹检测',
        'default_visual_role': 'hero',
        'default_tags': ['FibroScan', '福波看', '肝弹', '器械'],
    },
    {
        'key': 'fibroscan_family',
        'label': 'FibroScan 产品家族',
        'product_category': 'device',
        'product_name': 'FibroScan 产品家族',
        'product_indication': '肝脏无创监测 / 肝弹检测',
        'default_visual_role': 'family_lineup',
        'default_tags': ['FibroScan', '福波看', '产品家族', '器械'],
    },
    {
        'key': 'fufang_biejia_ruangan_pian',
        'label': '复方鳖甲软肝片（金装）',
        'product_category': 'medicine',
        'product_name': '复方鳖甲软肝片',
        'product_indication': '肝纤维化 / 肝硬化',
        'default_visual_role': 'standard_pack',
        'default_tags': ['复方鳖甲软肝片', '肝纤维化', '肝硬化', '药品'],
    },
    {
        'key': 'kezhi_jiaonang',
        'label': '壳脂胶囊',
        'product_category': 'medicine',
        'product_name': '壳脂胶囊',
        'product_indication': '脂肪肝',
        'default_visual_role': 'standard_pack',
        'default_tags': ['壳脂胶囊', '脂肪肝', '药品'],
    },
]

ASSET_STYLE_TYPE_DEFINITIONS = [
    {
        'key': 'medical_science',
        'label': '医学科普类',
        'description': '适合症状警示、器官对照、病理放大、检查解读这类“视觉说明书”型内容',
        'asset_type': '医学科普图',
        'family': 'medical_science',
        'generation_mode': 'text_to_image',
        'supports_reference_library': False,
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
        'label': '封面大字报类',
        'description': '适合作为通用大字报封面，适合强标题、情绪冲击、核心结论型内容',
        'asset_type': '大字报',
        'family': 'poster',
        'generation_mode': 'template_first',
        'supports_reference_library': False,
        'default_size': '1536x2048',
        'prompt_suffix': '强调一个主标题，视觉冲击强，适合封面传播，信息点精简。',
        'default_bullets': ['一句大结论', '一个关键提醒', '一条行动建议'],
        'accent': '#ef4e45',
        'bg': '#fff2f0',
        'layout_hint': '文字占据画面 60% 以上，标题拆成 2-4 行，关键词可加荧光底块',
        'visual_hint': '极简背景、特粗黑体或强手写字感，适合做多图首封',
        'reference_hint': '参考小红书高点击大字报封面、经验总结贴、警示提醒图的感觉',
        'text_policy': '大字报优先模板排字，不依赖模型直接生成大段中文，重点词单独高亮',
        'avoid_hint': '不要塞太多插图，不要排版松散，不要海报广告感',
    },
    {
        'key': 'poster_bold',
        'label': '大字报类-黑体警示',
        'description': '适合指南、警示、结论、版本说明这类一眼就要读懂的封面',
        'asset_type': '大字报',
        'family': 'poster',
        'generation_mode': 'template_first',
        'supports_reference_library': False,
        'default_size': '1536x2048',
        'prompt_suffix': '标题极大、黑体极粗、行距紧凑，像重磅警示牌。',
        'default_bullets': ['一个核心主题', '一个高亮关键词', '一个结果导向句'],
        'accent': '#18e05e',
        'bg': '#fffdfd',
        'layout_hint': '标题分 2-3 行，关键词加亮绿或亮黄底块，背景极简或带浅网格线',
        'visual_hint': '极简、强对比、缩略图下也要清楚可读',
        'reference_hint': '参考“肝硬化诊疗指南 2025版”这类大字报',
        'text_policy': '优先模板直出；关键词高亮，次要信息极少',
        'avoid_hint': '不要复杂装饰，不要大量说明文字，不要弱对比配色',
    },
    {
        'key': 'poster_handwritten',
        'label': '大字报类-手写经验',
        'description': '适合经验总结、第一人称共鸣、情绪表达和吐槽式封面',
        'asset_type': '经验大字报',
        'family': 'poster',
        'generation_mode': 'template_first',
        'supports_reference_library': False,
        'default_size': '1536x2048',
        'prompt_suffix': '字感带一点手写和情绪张力，像个人经验贴封面。',
        'default_bullets': ['第一人称经验', '一句情绪化总结', '一个共鸣点'],
        'accent': '#f5f053',
        'bg': '#fffaf3',
        'layout_hint': '标题竖向堆叠，关键词加荧光笔涂抹感底色，保留大量留白',
        'visual_hint': '情绪更强、像私人经验总结，而不是正规说明书',
        'reference_hint': '参考“照顾四年肝硬化父亲总结出来的经验”这类经验封面',
        'text_policy': '模板排字优先，允许少量 emoji 点缀，但重点还是标题本身',
        'avoid_hint': '不要做成广告文案，不要塞满副标题，不要像PPT',
    },
    {
        'key': 'checklist',
        'label': '清单类',
        'description': '适合作为通用清单入口，承载步骤、提醒、对比、食谱和报告解读等结构化内容',
        'asset_type': '清单',
        'family': 'checklist',
        'generation_mode': 'template_first',
        'supports_reference_library': False,
        'default_size': '1536x2048',
        'prompt_suffix': '清单结构，条目感强，适合打勾式阅读体验。',
        'default_bullets': ['先做什么', '中间检查什么', '最后复盘什么'],
        'accent': '#2d8f5a',
        'bg': '#f1fbf5',
        'layout_hint': '优先采用表格、时间轴、模块卡或报告说明框，结构比装饰更重要',
        'visual_hint': '像手账纸、网格纸、便签纸上的结构化答案图',
        'reference_hint': '参考产品选择表、7天食谱、白名单、彩超报告解读类图片',
        'text_policy': '强调数字、单位、勾选、时间轴和总结结论，适合截图收藏',
        'avoid_hint': '不要做成纯海报，不要只有插画没有结构，不要大段堆文字',
    },
    {
        'key': 'checklist_table',
        'label': '清单类-表格对比',
        'description': '适合产品怎么选、白名单、参数对比、品牌矩阵',
        'asset_type': '表格清单图',
        'family': 'checklist',
        'generation_mode': 'template_first',
        'supports_reference_library': False,
        'default_size': '1536x2048',
        'prompt_suffix': '重点做成清晰表格或矩阵，让人一眼知道怎么选。',
        'default_bullets': ['横向比较', '纵向指标', '最终推荐语'],
        'accent': '#f1c24b',
        'bg': '#fff9ea',
        'layout_hint': '网格/表格系统清楚，列头行头明确，可放真实产品抠图',
        'visual_hint': '像产品对比手账页，既整齐又可截图',
        'reference_hint': '参考奶粉怎么选、白名单、产品参数对比类图片',
        'text_policy': '数字和参数清晰，最终结论一定要直接给出',
        'avoid_hint': '不要只有长文，没有表格结构；不要配色太花',
    },
    {
        'key': 'checklist_timeline',
        'label': '清单类-时间轴食谱',
        'description': '适合 7 天食谱、一天多餐安排、执行计划、复查节奏',
        'asset_type': '时间轴清单图',
        'family': 'checklist',
        'generation_mode': 'template_first',
        'supports_reference_library': False,
        'default_size': '1536x2048',
        'prompt_suffix': '按时间和模块切开，强调什么时候吃、什么时候做。',
        'default_bullets': ['时间轴', '模块卡', '执行顺序'],
        'accent': '#ff7870',
        'bg': '#fff7f5',
        'layout_hint': '自上而下按时间/天数分区，圆角卡片清楚切开早餐、午餐、晚餐、加餐等环节',
        'visual_hint': '真实食物图或清单模块组合，实操感强',
        'reference_hint': '参考 7 天食谱、执行打卡表、复查时间表类图片',
        'text_policy': '时间、重量、份量和顺序要清楚，适合用户直接照着执行',
        'avoid_hint': '不要把时间轴做散，不要只写菜名不写时间和数量',
    },
    {
        'key': 'checklist_report',
        'label': '清单类-报告解读',
        'description': '适合彩超、化验单、指标说明、一次看懂报告',
        'asset_type': '报告解读图',
        'family': 'checklist',
        'generation_mode': 'template_first',
        'supports_reference_library': False,
        'default_size': '1536x2048',
        'prompt_suffix': '按项目逐条解释，像医生在报告边上做划重点。',
        'default_bullets': ['项目名', '表现含义', '下一步建议'],
        'accent': '#91c76f',
        'bg': '#f7fbf1',
        'layout_hint': '一列一项或一块一项，结合示意图、划线和圈注说明关键指标',
        'visual_hint': '像专业笔记和报告批注图，结构清楚、读起来不累',
        'reference_hint': '参考肝脏彩超一次看懂、ALT/AST 指标解读类图片',
        'text_policy': '指标名、结果表现和解释要一一对应，适合快速查阅',
        'avoid_hint': '不要只展示器官图不解释报告，不要跳过结论和下一步动作',
    },
    {
        'key': 'memo',
        'label': '备忘录类',
        'description': '适合作为通用备忘录入口，承载提醒、注意事项、问答记录和私人攻略感内容',
        'asset_type': '备忘录',
        'family': 'memo',
        'generation_mode': 'template_first',
        'supports_reference_library': False,
        'default_size': '1536x2048',
        'prompt_suffix': '像随手记下来的重点备忘，便签感、记录感强，但整体要整洁。',
        'default_bullets': ['今天先记住', '这类情况要留意', '复查前别忘了'],
        'accent': '#5c6ac4',
        'bg': '#f3f4ff',
        'layout_hint': '像手机备忘录或课堂笔记页，文字主导，少量贴纸和高亮点缀',
        'visual_hint': '真实、亲近、低广告感，像私人收藏的干货笔记',
        'reference_hint': '参考 iPhone 备忘录、课堂笔记、高亮重点总结类图片',
        'text_policy': '短句、碎片化表达、重点高亮，不靠长篇大论',
        'avoid_hint': '不要做成宣传海报，不要插画过多，不要满屏商业元素',
    },
    {
        'key': 'memo_mobile',
        'label': '备忘录类-手机备忘录',
        'description': '适合私人攻略、补救指南、生活方式建议、3-5 条操作清单',
        'asset_type': '手机备忘录图',
        'family': 'memo',
        'generation_mode': 'template_first',
        'supports_reference_library': False,
        'default_size': '1536x2048',
        'prompt_suffix': '尽量模拟手机原生备忘录界面，真实、简洁、可收藏。',
        'default_bullets': ['3-5 条短句要点', 'emoji 点缀', '重点高亮'],
        'accent': '#f4dc62',
        'bg': '#fffefe',
        'layout_hint': '顶部像原生备忘录界面，白底极简，数字清单+荧光高亮',
        'visual_hint': '像私人笔记，不像广告，留白要充足',
        'reference_hint': '参考 iPhone 备忘录风格、生活化攻略类图片',
        'text_policy': '每条不超过两行，重点词荧光笔高亮，可少量 emoji',
        'avoid_hint': '不要复杂背景，不要大面积插画，不要做成 PPT',
    },
    {
        'key': 'memo_classroom',
        'label': '备忘录类-课堂笔记',
        'description': '适合并发症整理、病理总结、检查要点、课堂板书式知识整理',
        'asset_type': '课堂笔记图',
        'family': 'memo',
        'generation_mode': 'template_first',
        'supports_reference_library': False,
        'default_size': '1536x2048',
        'prompt_suffix': '像医生或老师随手整理的重点课堂笔记，重点圈出、划线和批注明显。',
        'default_bullets': ['分点整理', '划重点', '箭头圈注'],
        'accent': '#b2d66b',
        'bg': '#fffef8',
        'layout_hint': '像复习资料页，主干标题+分点内容+荧光笔划重点+圈注',
        'visual_hint': '信息密度高但不拥挤，像手写课堂笔记而非宣传海报',
        'reference_hint': '参考肝硬化并发症、病理、生理板书笔记类图片',
        'text_policy': '重点内容短句化，并用高亮、下划线、括号和箭头做标注',
        'avoid_hint': '不要只有大段正文，不要做成普通知识卡，没有笔记感',
    },
    {
        'key': 'knowledge_card',
        'label': '知识卡片类',
        'description': '适合机制图、模块卡、故事化知识图谱、设备对比和收藏型内页',
        'asset_type': '知识卡片',
        'family': 'knowledge_card',
        'generation_mode': 'text_to_image',
        'supports_reference_library': False,
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
        'family': 'compare',
        'generation_mode': 'text_to_image',
        'supports_reference_library': False,
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
        'family': 'flow',
        'generation_mode': 'text_to_image',
        'supports_reference_library': False,
        'default_size': '1536x2048',
        'prompt_suffix': '流程步骤清晰，方向性强，适合路线图阅读方式。',
        'default_bullets': ['第一步', '第二步', '第三步'],
        'accent': '#f2a43c',
        'bg': '#fff8ea',
    },
    {
        'key': 'reference_based',
        'label': '参考图生成类',
        'description': '适合上传或选择参考图后，按参考图风格和构图方向去生成底图',
        'asset_type': '参考图风格生成',
        'family': 'reference_based',
        'generation_mode': 'reference_guided',
        'supports_reference_library': True,
        'default_size': '1536x2048',
        'prompt_suffix': '优先保持参考图的构图语言、留白结构、色彩气质和插画风格，但不要机械复制原图。',
        'default_bullets': ['继承参考图风格', '保留当前主题重点', '为后续叠字预留清晰区域'],
        'accent': '#8b6fd9',
        'bg': '#f6f2ff',
        'layout_hint': '优先参考风格图里的主体摆放、信息块结构和留白节奏，生成无字底图。',
        'visual_hint': '先做风格靠近的底图，不追求逐像素复制，重点保持气质、构图和元素组织。',
        'reference_hint': '适合你已经收集好的医学科普图、知识卡片图和产品视觉参考图。',
        'text_policy': '这类图优先生成无字底图，后续再由系统叠加中文标题和说明。',
        'avoid_hint': '不要把参考图原样临摹，不要直接抄现有文字，不要保留原图水印和品牌标识。',
    },
]

VOLCENGINE_MODEL_OPTIONS = [
    {'key': 'doubao-seedream-5-0-lite-260128', 'label': 'Seedream 5.0 lite', 'provider': 'volcengine_las'},
    {'key': 'doubao-seedream-5-0-260128', 'label': 'Seedream 5.0', 'provider': 'volcengine_las'},
    {'key': 'doubao-seedream-4-5-251128', 'label': 'Seedream 4.5', 'provider': 'volcengine_las'},
    {'key': 'doubao-seedream-4-0-250828', 'label': 'Seedream 4.0', 'provider': 'volcengine_las'},
    {'key': 'doubao-seededit-3-0-i2i-250628', 'label': 'SeedEdit 3.0', 'provider': 'volcengine_ark'},
]

OPENAI_IMAGE_MODEL_OPTIONS = [
    {'key': 'gpt-image-1', 'label': 'GPT Image', 'provider': 'openai'},
    {'key': 'openai-custom-image-model', 'label': '自定义 OpenAI 图片模型名', 'provider': 'openai'},
]

GENERIC_IMAGE_MODEL_OPTIONS = [
    {'key': 'custom-image-model', 'label': '自定义模型名', 'provider': 'generic'},
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
        'hotword_scope_preset': (os.environ.get('HOTWORD_SCOPE_PRESET') or '').strip(),
        'hotword_time_window': (os.environ.get('HOTWORD_TIME_WINDOW') or '').strip(),
        'hotword_date_from': (os.environ.get('HOTWORD_DATE_FROM') or '').strip(),
        'hotword_date_to': (os.environ.get('HOTWORD_DATE_TO') or '').strip(),
        'hotword_api_url': (os.environ.get('HOTWORD_API_URL') or '').strip(),
        'hotword_api_method': (os.environ.get('HOTWORD_API_METHOD') or '').strip(),
        'hotword_api_headers_json': (os.environ.get('HOTWORD_API_HEADERS_JSON') or '').strip(),
        'hotword_api_query_json': (os.environ.get('HOTWORD_API_QUERY_JSON') or '').strip(),
        'hotword_api_body_json': (os.environ.get('HOTWORD_API_BODY_JSON') or '').strip(),
        'hotword_result_path': (os.environ.get('HOTWORD_RESULT_PATH') or '').strip(),
        'hotword_keyword_param': (os.environ.get('HOTWORD_KEYWORD_PARAM') or '').strip(),
        'hotword_trend_type': (os.environ.get('HOTWORD_TREND_TYPE') or '').strip(),
        'hotword_auto_generate_topic_ideas': (os.environ.get('HOTWORD_AUTO_GENERATE_TOPIC_IDEAS') or '').strip(),
        'hotword_auto_convert_corpus_templates': (os.environ.get('HOTWORD_AUTO_CONVERT_CORPUS_TEMPLATES') or '').strip(),
    }
    timeout_value = (os.environ.get('HOTWORD_TIMEOUT_SECONDS') or '').strip()
    if timeout_value:
        env_overrides['hotword_timeout_seconds'] = _safe_int(timeout_value, config.get('hotword_timeout_seconds', 30))
    page_size_value = (os.environ.get('HOTWORD_PAGE_SIZE') or '').strip()
    if page_size_value:
        env_overrides['hotword_page_size'] = _safe_int(page_size_value, config.get('hotword_page_size', 20))
    max_related_queries_value = (os.environ.get('HOTWORD_MAX_RELATED_QUERIES') or '').strip()
    if max_related_queries_value:
        env_overrides['hotword_max_related_queries'] = _safe_int(max_related_queries_value, config.get('hotword_max_related_queries', 20))
    auto_generate_count = (os.environ.get('HOTWORD_AUTO_GENERATE_TOPIC_COUNT') or '').strip()
    if auto_generate_count:
        env_overrides['hotword_auto_generate_topic_count'] = _safe_int(auto_generate_count, config.get('hotword_auto_generate_topic_count', 20))
    auto_generate_activity = (os.environ.get('HOTWORD_AUTO_GENERATE_TOPIC_ACTIVITY_ID') or '').strip()
    if auto_generate_activity:
        env_overrides['hotword_auto_generate_topic_activity_id'] = _safe_int(auto_generate_activity, config.get('hotword_auto_generate_topic_activity_id', 0))
    auto_generate_quota = (os.environ.get('HOTWORD_AUTO_GENERATE_TOPIC_QUOTA') or '').strip()
    if auto_generate_quota:
        env_overrides['hotword_auto_generate_topic_quota'] = _safe_int(auto_generate_quota, config.get('hotword_auto_generate_topic_quota', 30))
    auto_convert_limit = (os.environ.get('HOTWORD_AUTO_CONVERT_CORPUS_LIMIT') or '').strip()
    if auto_convert_limit:
        env_overrides['hotword_auto_convert_corpus_limit'] = _safe_int(auto_convert_limit, config.get('hotword_auto_convert_corpus_limit', 10))

    for key, value in env_overrides.items():
        if value not in [None, '']:
            config[key] = value
    config['hotword_timeout_seconds'] = min(max(_safe_int(config.get('hotword_timeout_seconds'), 30), 5), 120)
    config['hotword_fetch_mode'] = (config.get('hotword_fetch_mode') or 'auto').strip().lower() or 'auto'
    config['hotword_scope_preset'] = (config.get('hotword_scope_preset') or 'liver_comorbidity').strip() or 'liver_comorbidity'
    config['hotword_time_window'] = (config.get('hotword_time_window') or '30d').strip().lower() or '30d'
    if config['hotword_time_window'] not in {'3d', '7d', '30d', 'custom'}:
        config['hotword_time_window'] = '30d'
    config['hotword_date_from'] = (config.get('hotword_date_from') or '').strip()
    config['hotword_date_to'] = (config.get('hotword_date_to') or '').strip()
    config['hotword_api_method'] = (config.get('hotword_api_method') or 'GET').strip().upper() or 'GET'
    config['hotword_keyword_param'] = (config.get('hotword_keyword_param') or 'keyword').strip() or 'keyword'
    config['hotword_trend_type'] = (config.get('hotword_trend_type') or 'note_search').strip().lower() or 'note_search'
    if config['hotword_trend_type'] not in {'note_search', 'hot_queries'}:
        config['hotword_trend_type'] = 'note_search'
    config['hotword_page_size'] = min(max(_safe_int(config.get('hotword_page_size'), 20), 1), 50)
    config['hotword_max_related_queries'] = min(max(_safe_int(config.get('hotword_max_related_queries'), 20), 1), 50)
    config['hotword_auto_generate_topic_ideas'] = str(config.get('hotword_auto_generate_topic_ideas') or '').strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
    config['hotword_auto_generate_topic_count'] = min(max(_safe_int(config.get('hotword_auto_generate_topic_count'), 20), 1), 120)
    config['hotword_auto_generate_topic_activity_id'] = max(_safe_int(config.get('hotword_auto_generate_topic_activity_id'), 0), 0)
    config['hotword_auto_generate_topic_quota'] = min(max(_safe_int(config.get('hotword_auto_generate_topic_quota'), 30), 1), 300)
    config['hotword_auto_convert_corpus_templates'] = str(config.get('hotword_auto_convert_corpus_templates') or '').strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
    config['hotword_auto_convert_corpus_limit'] = min(max(_safe_int(config.get('hotword_auto_convert_corpus_limit'), 10), 1), 50)
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
    current_month_only_value = (os.environ.get('CREATOR_SYNC_CURRENT_MONTH_ONLY') or '').strip()
    if current_month_only_value:
        env_overrides['creator_sync_current_month_only'] = current_month_only_value
    date_from_value = (os.environ.get('CREATOR_SYNC_DATE_FROM') or '').strip()
    if date_from_value:
        env_overrides['creator_sync_date_from'] = date_from_value
    date_to_value = (os.environ.get('CREATOR_SYNC_DATE_TO') or '').strip()
    if date_to_value:
        env_overrides['creator_sync_date_to'] = date_to_value
    max_posts_value = (os.environ.get('CREATOR_SYNC_MAX_POSTS_PER_ACCOUNT') or '').strip()
    if max_posts_value:
        env_overrides['creator_sync_max_posts_per_account'] = _safe_int(max_posts_value, config.get('creator_sync_max_posts_per_account', 60))

    for key, value in env_overrides.items():
        if value not in [None, '']:
            config[key] = value
    config['creator_sync_source_channel'] = (config.get('creator_sync_source_channel') or 'Crawler服务').strip() or 'Crawler服务'
    config['creator_sync_fetch_mode'] = (config.get('creator_sync_fetch_mode') or 'auto').strip().lower() or 'auto'
    config['creator_sync_api_method'] = (config.get('creator_sync_api_method') or 'POST').strip().upper() or 'POST'
    config['creator_sync_timeout_seconds'] = min(max(_safe_int(config.get('creator_sync_timeout_seconds'), 60), 5), 300)
    config['creator_sync_batch_limit'] = min(max(_safe_int(config.get('creator_sync_batch_limit'), 20), 1), 200)
    config['creator_sync_current_month_only'] = str(config.get('creator_sync_current_month_only', 'true')).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
    config['creator_sync_date_from'] = (config.get('creator_sync_date_from') or '').strip()
    config['creator_sync_date_to'] = (config.get('creator_sync_date_to') or '').strip()
    config['creator_sync_max_posts_per_account'] = min(max(_safe_int(config.get('creator_sync_max_posts_per_account'), 60), 1), 100)
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


def _product_category_options():
    return [dict(item) for item in PRODUCT_CATEGORY_OPTIONS]


def _product_visual_role_options():
    return [dict(item) for item in PRODUCT_VISUAL_ROLE_OPTIONS]


def _product_profile_options():
    return [dict(item) for item in PRODUCT_PROFILE_DEFINITIONS]


def _product_profile_meta(profile_key=''):
    raw = (profile_key or '').strip()
    for item in PRODUCT_PROFILE_DEFINITIONS:
        if raw == item['key'] or raw == item['label'] or raw == item['product_name']:
            return dict(item)
    return {}


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
    if current_provider in {'openai', 'openai_compatible'}:
        return [dict(item) for item in OPENAI_IMAGE_MODEL_OPTIONS]
    return [dict(item) for item in GENERIC_IMAGE_MODEL_OPTIONS]


def _resolve_image_provider_api_key(provider=''):
    safe_provider = (provider or '').strip() or 'svg_fallback'
    if safe_provider == 'openai':
        return (
            os.environ.get('ASSET_IMAGE_API_KEY')
            or os.environ.get('OPENAI_IMAGE_API_KEY')
            or os.environ.get('OPENAI_API_KEY')
            or ''
        ).strip()
    if safe_provider == 'openai_compatible':
        return (
            os.environ.get('ASSET_IMAGE_API_KEY')
            or os.environ.get('OPENAI_IMAGE_API_KEY')
            or os.environ.get('OPENAI_API_KEY')
            or os.environ.get('ARK_API_KEY')
            or os.environ.get('LAS_API_KEY')
            or ''
        ).strip()
    if safe_provider == 'volcengine_ark':
        return (
            os.environ.get('ASSET_IMAGE_API_KEY')
            or os.environ.get('ARK_API_KEY')
            or ''
        ).strip()
    if safe_provider == 'volcengine_las':
        return (
            os.environ.get('ASSET_IMAGE_API_KEY')
            or os.environ.get('LAS_API_KEY')
            or ''
        ).strip()
    return (
        os.environ.get('ASSET_IMAGE_API_KEY')
        or os.environ.get('IMAGE_API_KEY')
        or os.environ.get('OPENAI_IMAGE_API_KEY')
        or os.environ.get('OPENAI_API_KEY')
        or ''
    ).strip()


def _image_provider_capabilities():
    runtime_config = _automation_runtime_config()
    provider = (os.environ.get('ASSET_IMAGE_PROVIDER') or str(runtime_config.get('image_provider') or 'svg_fallback')).strip() or 'svg_fallback'
    api_base = (os.environ.get('ASSET_IMAGE_API_BASE') or str(runtime_config.get('image_api_base') or '')).strip()
    if provider == 'volcengine_ark' and not api_base:
        api_base = 'https://ark.cn-beijing.volces.com/api/v3'
    if provider == 'volcengine_las' and not api_base:
        api_base = 'https://operator.las.cn-beijing.volces.com/api/v1'
    if provider == 'openai' and not api_base:
        api_base = 'https://api.openai.com/v1'
    api_url = (os.environ.get('ASSET_IMAGE_API_URL') or str(runtime_config.get('image_api_url') or '')).strip()
    if not api_url and api_base:
        api_url = api_base.rstrip('/') + '/images/generations'
    api_key = _resolve_image_provider_api_key(provider)
    model_name = (os.environ.get('ASSET_IMAGE_MODEL') or str(runtime_config.get('image_model') or '')).strip()
    if not model_name and provider in {'volcengine_ark', 'volcengine_las'}:
        model_name = 'doubao-seedream-5-0-lite-260128'
    if not model_name and provider in {'openai', 'openai_compatible'}:
        model_name = 'gpt-image-1'
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
