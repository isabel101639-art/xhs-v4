from copy import deepcopy


DEFAULT_COPY_SKILL_KEY = 'story_empathy'

COPY_SKILL_OPTIONS = {
    'auto': '系统自动匹配',
    'story_empathy': '经历共鸣型',
    'report_interpretation': '检查解读型',
    'practical_checklist': '收藏清单型',
    'myth_busting': '反常识拆解型',
    'discussion_hook': '互动讨论型',
}

_COPY_SKILL_PROFILES = {
    'story_empathy': {
        'label': '经历共鸣型',
        'description': '先把真实经历、情绪波动和场景细节讲出来，再自然带出经验和管理建议。',
        'title_rule': '标题更像“我后来才知道”“那次之后我不敢再拖”的真实分享，不要像说明书。',
        'hook_rule': '开头先抛出一个具体瞬间、情绪或反应，让读者先代入，再展开解释。',
        'body_rule': '正文按“发生了什么 -> 我怎么理解 -> 我后来怎么做”来写，保留真实感。',
        'insertion_rule': '软植入只放在经历转折点顺手带出，不单独写产品卖点段落。',
        'ending_rule': '结尾像同类人交流，问对方会怎么做或有没有类似经历。',
        'avoid_rule': '避免满篇大道理、模板口吻和一上来就讲产品功能。',
        'variants': ['经历自述版', '陪伴观察版', '情绪转折版'],
        'local_titles': [
            '{lead_keyword}这件事我真的拖过',
            '那次因为{lead_keyword}，我一下警惕了',
            '关于{lead_keyword}，我是吃过亏才懂',
        ],
        'local_hooks': [
            '那天碰到{lead_keyword}的时候，我第一反应不是紧张，而是想再等等看。',
            '如果不是最近亲自经历了一次，我可能还会把{lead_keyword}当小事。',
            '我以前一直觉得{lead_keyword}离自己还远，直到那次真的撞上。',
        ],
        'local_body_lines': [
            '我想把那次在{scene_text}里的真实感受讲出来，这样比空讲道理更容易让人代入。',
            '后来我才意识到，{lead_keyword}最怕的不是不知道，而是明明有提醒还一直往后拖。',
            '{focus_hint}',
        ],
        'local_endings': [
            '你们遇到这种情况，会先安慰自己再看看，还是马上去确认？',
            '如果是你，会从哪一步开始调整？',
            '有过类似经历的人，会怎么跟家里人解释这件事？',
        ],
    },
    'report_interpretation': {
        'label': '检查解读型',
        'description': '把报告、指标、复查和判断逻辑讲清楚，帮不会写的人把“专业感”写得更自然。',
        'title_rule': '标题突出“别只盯一个指标”“复查时真正该看什么”，像懂门道的人在提醒。',
        'hook_rule': '开头从体检单、报告单、复查对比里的一个细节点切入，别空泛。',
        'body_rule': '正文优先写指标变化、容易误判的点和接下来该做什么，结构清晰但口语化。',
        'insertion_rule': '若要带出检查或产品，只能放在解释判断逻辑时顺势提到。',
        'ending_rule': '结尾适合问大家复查时最在意哪个指标，或有没有被某个指标误导过。',
        'avoid_rule': '避免写成教科书或只堆术语，不要让人觉得在上课。',
        'variants': ['指标提醒版', '复查对比版', '报告拆解版'],
        'local_titles': [
            '{lead_keyword}别只看一个数',
            '复查看到{lead_keyword}，我先看这几点',
            '{lead_keyword}有变化时，先别急着慌',
        ],
        'local_hooks': [
            '我后来才发现，很多人看到报告里有{lead_keyword}，第一反应就已经跑偏了。',
            '那次拿到复查单时，我盯着{lead_keyword}看了很久，后来才知道不能只看这一项。',
            '如果体检单上出现{lead_keyword}，我更建议先把前后变化和背景一起看。',
        ],
        'local_body_lines': [
            '我会先把报告里最容易被误读的点拆开讲清楚，不然很多人看完还是只剩焦虑。',
            '真正有用的不是背术语，而是知道{lead_keyword}放到复查趋势和生活状态里该怎么判断。',
            '{focus_hint}',
        ],
        'local_endings': [
            '你们复查时最在意哪个指标？',
            '如果报告里只看到一个异常项，你们会先去查资料还是先问医生？',
            '大家拿到复查单时，最容易被哪个词吓到？',
        ],
    },
    'practical_checklist': {
        'label': '收藏清单型',
        'description': '把内容写成可收藏的步骤、提醒和避坑清单，适合不会展开写故事的用户。',
        'title_rule': '标题要有步骤感、清单感和收藏价值，像“先做这3步”“这几件事别漏掉”。',
        'hook_rule': '开头先告诉读者这篇能帮他省什么事、少踩什么坑。',
        'body_rule': '正文尽量分步骤、分判断点写，句子短一些，结论更利于截图收藏。',
        'insertion_rule': '软植入只能放在某一步骤或某个提醒里，不可以整段推销。',
        'ending_rule': '结尾适合补一句“如果你还有别的经验也可以补充”，保持开放感。',
        'avoid_rule': '避免绕太多情绪线，重点给人“拿来就能用”的感觉。',
        'variants': ['三步清单版', '避坑提醒版', '复查备忘版'],
        'local_titles': [
            '{lead_keyword}先做这3步',
            '碰到{lead_keyword}，这几件事别漏',
            '关于{lead_keyword}，我会先按这个顺序来',
        ],
        'local_hooks': [
            '如果你最近也碰到{lead_keyword}，这篇我尽量只讲能直接拿来用的部分。',
            '我把和{lead_keyword}有关的重点压成了几步，方便你直接照着排。',
            '很多人不是不重视{lead_keyword}，而是不知道第一步该做什么。',
        ],
        'local_body_lines': [
            '这篇我不想写虚的，直接把先后顺序、重点判断和容易漏掉的动作列清楚。',
            '比起一下子搜很多资料，先把{lead_keyword}相关的关键动作按顺序做完更重要。',
            '{focus_hint}',
        ],
        'local_endings': [
            '如果你还有自己整理过的实用步骤，也欢迎一起补充。',
            '你们一般会把哪一步排在最前面？',
            '还有哪些你觉得特别值得补上的提醒？',
        ],
    },
    'myth_busting': {
        'label': '反常识拆解型',
        'description': '先打破一个常见误区，再解释为什么很多人会想错，适合点击率导向的文案。',
        'title_rule': '标题带一点反差或误区感，比如“别再以为……”“很多人都误会了……”。',
        'hook_rule': '开头先抛出常见误解，再用一句经历或判断把它翻过来。',
        'body_rule': '正文先说大家为什么会误会，再给出更靠谱的理解和动作建议。',
        'insertion_rule': '软植入只能作为“更靠谱做法”的一部分，不能把误区拆解写成广告转场。',
        'ending_rule': '结尾适合问大家以前是不是也这么想过，制造共鸣和互动。',
        'avoid_rule': '避免故意夸张或制造恐慌，重点是纠偏，不是吓人。',
        'variants': ['误区拆解版', '反差提醒版', '踩坑复盘版'],
        'local_titles': [
            '{lead_keyword}别再想当然了',
            '很多人对{lead_keyword}都误会了',
            '关于{lead_keyword}，我以前也想错过',
        ],
        'local_hooks': [
            '我以前对{lead_keyword}最大的误解，就是以为再等等也没关系。',
            '很多人一提{lead_keyword}就会往一个方向想，但真正容易踩坑的恰恰不是那个点。',
            '如果你也把{lead_keyword}想得太简单，这篇可能正好能帮你纠偏。',
        ],
        'local_body_lines': [
            '后来我才发现，很多人不是不关心{lead_keyword}，而是被一些顺口却不准确的说法带偏了。',
            '这篇我会把最常见的误区和更稳妥的处理思路拆开讲，不让内容只停在“知道了”。',
            '{focus_hint}',
        ],
        'local_endings': [
            '你以前也有过这种误解吗？',
            '如果不是后来被提醒，你会不会也继续按原来的想法走？',
            '还有哪些关于这件事的误区，是你后来才意识到的？',
        ],
    },
    'discussion_hook': {
        'label': '互动讨论型',
        'description': '把观点、选择题和真实纠结感写出来，适合希望多评论、多交流的场景。',
        'title_rule': '标题给出一个立场冲突、选择题或真实纠结点，留出讨论空间。',
        'hook_rule': '开头先抛问题或冲突，不要直接给标准答案。',
        'body_rule': '正文要把纠结的原因、不同选择各自的顾虑讲明白，让人愿意接话。',
        'insertion_rule': '软植入只能作为其中一种选择或经验，不要压掉讨论空间。',
        'ending_rule': '结尾直接问大家会怎么选、遇到这种情况通常怎么判断。',
        'avoid_rule': '避免一锤定音式说教，重点是把话题打开。',
        'variants': ['站队提问版', '经历讨论版', '选择纠结版'],
        'local_titles': [
            '{lead_keyword}这种情况，你会怎么选',
            '碰到{lead_keyword}，大家一般先做哪一步',
            '如果是你，{lead_keyword}会怎么处理',
        ],
        'local_hooks': [
            '关于{lead_keyword}，我最近一直在想，到底是先观察一下还是立刻处理更稳。',
            '每次聊到{lead_keyword}，我都发现大家的反应差别特别大。',
            '如果把{lead_keyword}放到真实生活里，很多人的选择其实不会完全一样。',
        ],
        'local_body_lines': [
            '我想把自己纠结的点摊开讲，这样看到的人也更容易代入自己的处境。',
            '很多时候不是不知道答案，而是不同做法各有顾虑，真正难的是怎么取舍。',
            '{focus_hint}',
        ],
        'local_endings': [
            '如果换成你，会怎么选？',
            '你们碰到这种情况，通常会先听谁的建议？',
            '大家更倾向先观察，还是先把能做的动作做起来？',
        ],
    },
}


def _auto_skill_key(topic_text='', copy_goal='balanced'):
    text = (topic_text or '').strip()
    if copy_goal == 'comment_engagement':
        return 'discussion_hook'
    if copy_goal == 'save_value':
        return 'practical_checklist'
    if any(key in text for key in ['体检', '检查', '报告', '指标', 'FibroScan', '福波看', '复查']):
        return 'report_interpretation'
    if copy_goal == 'viral_title':
        return 'myth_busting'
    return DEFAULT_COPY_SKILL_KEY


def resolve_copy_skill(skill_key='auto', topic_text='', copy_goal='balanced'):
    key = (skill_key or 'auto').strip()
    if key == 'auto':
        key = _auto_skill_key(topic_text=topic_text, copy_goal=copy_goal)
    if key not in _COPY_SKILL_PROFILES:
        key = DEFAULT_COPY_SKILL_KEY
    profile = deepcopy(_COPY_SKILL_PROFILES[key])
    profile['key'] = key
    return profile


def build_copy_skill_prompt_block(profile):
    item = profile or resolve_copy_skill()
    return '\n'.join([
        f"技能包：{item['label']}",
        f"说明：{item['description']}",
        f"标题策略：{item['title_rule']}",
        f"开头策略：{item['hook_rule']}",
        f"正文策略：{item['body_rule']}",
        f"软植入策略：{item['insertion_rule']}",
        f"互动策略：{item['ending_rule']}",
        f"避免事项：{item['avoid_rule']}",
    ]).strip()


def build_copy_skill_local_guidance(profile, lead_keyword='', prompt_focus='', scene_text=''):
    item = profile or resolve_copy_skill()
    format_values = {
        'lead_keyword': lead_keyword or '护肝管理',
        'focus_hint': f'这次我会重点把“{prompt_focus}”这个点说透。' if prompt_focus else '这次我会把最容易被忽略的细节和判断点讲清楚。',
        'scene_text': scene_text or '日常护肝管理',
    }

    def render(items):
        return [str(text).format(**format_values).strip() for text in (items or []) if str(text).strip()]

    return {
        'titles': render(item.get('local_titles')),
        'hooks': render(item.get('local_hooks')),
        'body_lines': render(item.get('local_body_lines')),
        'endings': render(item.get('local_endings')),
    }


DEFAULT_TITLE_SKILL_KEY = 'result_first'

TITLE_SKILL_OPTIONS = {
    'auto': '系统自动匹配',
    'result_first': '结果前置标题',
    'conflict_reverse': '反差纠偏标题',
    'question_gap': '提问悬念标题',
    'checklist_collect': '收藏清单标题',
    'emotional_diary': '经历情绪标题',
}

_TITLE_SKILL_PROFILES = {
    'result_first': {
        'label': '结果前置标题',
        'description': '标题先给结论、提醒或结果，适合点击率和明确价值导向。',
        'title_rule': '标题先亮结果或提醒，例如“别再……”“先看这几点”“我后来才知道……”。',
        'avoid_rule': '避免标题太空、太像广告，尽量让人一眼看懂这篇解决什么问题。',
        'local_titles': [
            '{lead_keyword}先看这几点',
            '关于{lead_keyword}，我后来先改了这一点',
            '{topic_name}这件事，别再拖了',
        ],
    },
    'conflict_reverse': {
        'label': '反差纠偏标题',
        'description': '先打破常见误解，用反差感带点击。',
        'title_rule': '标题用“别再以为”“很多人都搞反了”“最容易误会的不是……”这类纠偏句式。',
        'avoid_rule': '不要为了冲突故意夸张，更像经验提醒，不像标题党。',
        'local_titles': [
            '{lead_keyword}别再想当然了',
            '很多人把{lead_keyword}搞反了',
            '关于{lead_keyword}，最容易误会的不是这一步',
        ],
    },
    'question_gap': {
        'label': '提问悬念标题',
        'description': '标题留出讨论空间，适合拉评论和互动。',
        'title_rule': '标题用选择题、提问句或两难句式，让读者忍不住想代入回答。',
        'avoid_rule': '不要问得太泛，要让问题足够具体，和真实情境贴合。',
        'local_titles': [
            '{lead_keyword}这种情况，你会怎么选',
            '如果是你，{lead_keyword}会先处理哪一步',
            '碰到{lead_keyword}，你会先观察还是马上确认',
        ],
    },
    'checklist_collect': {
        'label': '收藏清单标题',
        'description': '标题突出步骤、清单、总结，适合提高收藏率。',
        'title_rule': '标题像“先做这3步”“这几件事别漏”“按这个顺序来”，强调拿来就能用。',
        'avoid_rule': '不要把标题写成流水账，重点是精炼、好记、可截图。',
        'local_titles': [
            '{lead_keyword}先做这3步',
            '碰到{lead_keyword}，这几件事别漏',
            '关于{lead_keyword}，我会先按这个顺序来',
        ],
    },
    'emotional_diary': {
        'label': '经历情绪标题',
        'description': '标题更像真人经历，适合做共鸣和停留。',
        'title_rule': '标题像“我那次真的慌了”“后来我才知道”“这件事我拖过”，保留情绪转折。',
        'avoid_rule': '避免过度煽情，重点是自然可信，不要像演戏。',
        'local_titles': [
            '{lead_keyword}这件事我真的拖过',
            '那次因为{lead_keyword}，我一下警惕了',
            '关于{lead_keyword}，我是吃过亏才懂',
        ],
    },
}


def _auto_title_skill_key(topic_text='', copy_goal='balanced', copy_skill_key=''):
    text = (topic_text or '').strip()
    if copy_goal == 'save_value':
        return 'checklist_collect'
    if copy_goal == 'comment_engagement':
        return 'question_gap'
    if copy_goal == 'viral_title':
        return 'conflict_reverse'
    if copy_skill_key == 'story_empathy':
        return 'emotional_diary'
    if any(key in text for key in ['体检', '检查', '报告', '指标', 'FibroScan', '福波看', '复查']):
        return 'checklist_collect'
    return DEFAULT_TITLE_SKILL_KEY


def resolve_title_skill(skill_key='auto', topic_text='', copy_goal='balanced', copy_skill_key=''):
    key = (skill_key or 'auto').strip()
    if key == 'auto':
        key = _auto_title_skill_key(topic_text=topic_text, copy_goal=copy_goal, copy_skill_key=copy_skill_key)
    if key not in _TITLE_SKILL_PROFILES:
        key = DEFAULT_TITLE_SKILL_KEY
    profile = deepcopy(_TITLE_SKILL_PROFILES[key])
    profile['key'] = key
    return profile


def build_title_skill_prompt_block(profile):
    item = profile or resolve_title_skill()
    return '\n'.join([
        f"标题技能包：{item['label']}",
        f"说明：{item['description']}",
        f"标题要求：{item['title_rule']}",
        f"避免事项：{item['avoid_rule']}",
    ]).strip()


def build_title_skill_local_guidance(profile, lead_keyword='', topic_name=''):
    item = profile or resolve_title_skill()
    format_values = {
        'lead_keyword': lead_keyword or '护肝管理',
        'topic_name': (topic_name or lead_keyword or '护肝管理')[:16],
    }

    def render(items):
        return [str(text).format(**format_values).strip() for text in (items or []) if str(text).strip()]

    return {
        'titles': render(item.get('local_titles')),
    }


DEFAULT_IMAGE_SKILL_KEY = 'high_click_cover'

IMAGE_SKILL_OPTIONS = {
    'auto': '系统自动匹配',
    'high_click_cover': '高点击封面型',
    'save_worthy_cards': '高收藏干货型',
    'report_decode': '报告解读型',
    'story_atmosphere': '故事陪伴型',
    'classroom_focus': '课堂笔记型',
}

_IMAGE_SKILL_PROFILES = {
    'high_click_cover': {
        'label': '高点击封面型',
        'description': '优先做第一眼抓人的封面，适合冲点击、冲停留。',
        'family_key': 'poster',
        'mode_key': 'smart_bundle',
        'cover_style_key': 'poster_bold',
        'inner_style_key': 'knowledge_card',
        'usage_tip': '封面主打一个强结论、大字和情绪冲击，内页再补解释。',
    },
    'save_worthy_cards': {
        'label': '高收藏干货型',
        'description': '优先做可截图、可收藏、可复看的清单和知识卡。',
        'family_key': 'checklist',
        'mode_key': 'smart_bundle',
        'cover_style_key': 'checklist',
        'inner_style_key': 'checklist_report',
        'usage_tip': '适合步骤、判断点、对照表、避坑清单这类内容。',
    },
    'report_decode': {
        'label': '报告解读型',
        'description': '优先把指标、报告和判断逻辑画清楚，适合医疗科普和复查内容。',
        'family_key': 'medical_science',
        'mode_key': 'smart_bundle',
        'cover_style_key': 'medical_science',
        'inner_style_key': 'checklist_report',
        'usage_tip': '适合体检单、检查报告、复查趋势、指标说明这类图文。',
    },
    'story_atmosphere': {
        'label': '故事陪伴型',
        'description': '优先做更像真人分享的封面和内页，适合经历型和陪伴型内容。',
        'family_key': 'memo',
        'mode_key': 'smart_bundle',
        'cover_style_key': 'memo_mobile',
        'inner_style_key': 'memo_classroom',
        'usage_tip': '适合“我当时怎么想”“后来怎么做”这类陪伴感表达。',
    },
    'classroom_focus': {
        'label': '课堂笔记型',
        'description': '优先做结构化知识拆解，适合课堂感、笔记感、重点提炼。',
        'family_key': 'knowledge_card',
        'mode_key': 'smart_bundle',
        'cover_style_key': 'knowledge_card',
        'inner_style_key': 'memo_classroom',
        'usage_tip': '适合原理解释、知识整理、误区拆解和问答总结。',
    },
}


def _auto_image_skill_key(topic_text='', copy_goal='balanced', copy_skill_key=''):
    text = (topic_text or '').strip()
    if any(key in text for key in ['体检', '检查', '报告', '指标', 'FibroScan', '福波看', '复查']):
        return 'report_decode'
    if copy_goal == 'save_value':
        return 'save_worthy_cards'
    if copy_goal == 'comment_engagement':
        return 'story_atmosphere'
    if copy_goal == 'viral_title':
        return 'high_click_cover'
    if copy_skill_key == 'story_empathy':
        return 'story_atmosphere'
    return DEFAULT_IMAGE_SKILL_KEY


def resolve_image_skill(skill_key='auto', topic_text='', copy_goal='balanced', copy_skill_key=''):
    key = (skill_key or 'auto').strip()
    if key == 'auto':
        key = _auto_image_skill_key(topic_text=topic_text, copy_goal=copy_goal, copy_skill_key=copy_skill_key)
    if key not in _IMAGE_SKILL_PROFILES:
        key = DEFAULT_IMAGE_SKILL_KEY
    profile = deepcopy(_IMAGE_SKILL_PROFILES[key])
    profile['key'] = key
    return profile


def get_image_skill_presets():
    return deepcopy(_IMAGE_SKILL_PROFILES)
