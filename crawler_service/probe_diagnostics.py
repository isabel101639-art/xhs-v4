def _unique(items):
    result = []
    for item in items or []:
        text = str(item or '').strip()
        if text and text not in result:
            result.append(text)
    return result


def build_metric_coverage(items, metric_keys):
    items = items or []
    metric_keys = [str(item).strip() for item in (metric_keys or []) if str(item).strip()]
    coverage = {}
    total_count = len([item for item in items if isinstance(item, dict)])
    for metric_key in metric_keys:
        hit_count = 0
        source_paths = []
        for item in items:
            if not isinstance(item, dict):
                continue
            value = item.get(metric_key)
            if value in [None, '']:
                continue
            try:
                numeric_value = int(value)
            except (TypeError, ValueError):
                numeric_value = 0
            if numeric_value <= 0:
                continue
            hit_count += 1
            source = (item.get('metric_sources') or {}).get(metric_key)
            if source and source not in source_paths:
                source_paths.append(source)
        coverage[metric_key] = {
            'hit_count': hit_count,
            'total_count': total_count,
            'hit_rate': round((hit_count / total_count) * 100, 2) if total_count else 0,
            'source_paths': source_paths[:10],
        }
    return coverage


def build_login_state_diagnosis(result):
    result = result or {}
    health = result.get('health') or {}
    home = result.get('home') or {}
    search = result.get('search') or {}
    provider = result.get('provider') or ''

    issues = []
    actions = []

    if provider == 'playwright_xhs' and not result.get('storage_state_exists', False):
        issues.append('未找到 Playwright 登录态文件')
        actions.append('先运行 crawler_service/scripts/save_xhs_storage_state.py 保存登录态')

    if result.get('xhs_cookie_count', 0) <= 0:
        issues.append('登录态里没有可用的小红书 Cookie')
        actions.append('重新保存登录态，并确认扫码后再回车写入 storage state')

    if home.get('login_prompt_detected'):
        issues.append('首页仍然出现登录提示，登录态可能已失效')
        actions.append('重新登录小红书后再次保存 storage state')

    if search.get('login_prompt_detected'):
        issues.append('搜索页仍然出现登录提示，搜索结果可能被拦截')
        actions.append('优先重新登录，并用 verify_xhs_login_state.py 再验证一次')

    if result.get('xhs_cookie_count', 0) > 0 and not home.get('login_prompt_detected') and not search.get('login_prompt_detected'):
        if search.get('state_note_count', 0) > 0 or search.get('state_related_query_count', 0) > 0:
            return {
                'status': 'ready',
                'summary': '登录态看起来有效，搜索页状态数据已可读取',
                'issues': [],
                'suggested_actions': [
                    '可以继续运行 probe_xhs_trends.py 或 probe_xhs_bundle.py 做真实抓取联调',
                ],
            }
        issues.append('登录态看起来可用，但搜索页状态数据还没有解析出样例内容')
        actions.extend([
            '先运行 crawler_service/scripts/debug_xhs_search.py 检查搜索页截图和 HTML',
            '如果页面已打开但无结果，优先检查关键词是否过于冷门',
        ])

    status = 'blocked' if any(token in ' '.join(issues) for token in ['未找到', '没有可用', '登录提示']) else 'partial'
    summary = '登录态暂不可直接用于真实联调' if status == 'blocked' else '登录态部分可用，但还需要补调试'
    return {
        'status': status,
        'summary': summary,
        'issues': _unique(issues),
        'suggested_actions': _unique(actions),
    }


def build_trend_probe_diagnosis(summary):
    summary = summary or {}
    health = summary.get('health') or {}
    provider = summary.get('provider') or ''
    item_count = summary.get('item_count', 0) or 0
    trend_type = summary.get('trend_type') or 'note_search'
    sample_items = summary.get('sample_items') or []
    has_nonzero_views = any((item.get('views') or 0) > 0 for item in sample_items if isinstance(item, dict))
    has_nonzero_hot_value = any((item.get('hot_value') or 0) > 0 for item in sample_items if isinstance(item, dict))

    if provider == 'playwright_xhs' and not health.get('storage_state_exists', False):
        return {
            'status': 'blocked',
            'summary': '未找到 Playwright 登录态文件，无法做真实热点抓取',
            'issues': ['未找到登录态文件'],
            'suggested_actions': ['先运行 crawler_service/scripts/save_xhs_storage_state.py 保存登录态'],
        }

    if item_count > 0:
        if trend_type == 'note_search' and has_nonzero_views and not has_nonzero_hot_value:
            return {
                'status': 'partial',
                'summary': '已抓到爆款笔记和阅读量，但热度值仍未稳定命中',
                'issues': ['当前热度值主要依赖阅读/互动估算或页面未返回稳定热度字段'],
                'suggested_actions': [
                    '优先检查搜索页状态树里是否存在 hot_value / score / search_cnt 一类字段',
                    '继续用 debug_xhs_search.py 查看状态树样例，必要时补充热度字段路径',
                ],
            }
        return {
            'status': 'ready',
            'summary': f'已成功抓到 {item_count} 条{"爆款笔记" if trend_type == "note_search" else "相关热搜词"}',
            'issues': [],
            'suggested_actions': ['可以把同样参数配置到自动化中心并测试热点 Worker 落库'],
        }

    return {
        'status': 'partial',
        'summary': '热点抓取已执行，但还没有返回可用结果',
        'issues': ['当前关键词未抓到结果，或页面状态结构仍需校准'],
        'suggested_actions': _unique([
            '先运行 crawler_service/scripts/verify_xhs_login_state.py 验证登录态',
            '再运行 crawler_service/scripts/debug_xhs_search.py 检查搜索页截图和状态数据',
            '尝试更热门的关键词，例如“脂肪肝”或“肝纤维化”',
        ]),
    }


def build_account_probe_diagnosis(summary):
    summary = summary or {}
    health = summary.get('health') or {}
    provider = summary.get('provider') or ''
    account_count = summary.get('account_count', 0) or 0
    post_count = summary.get('post_count', 0) or 0
    sample_posts = summary.get('sample_posts') or []
    has_nonzero_views = any((item.get('views') or 0) > 0 for item in sample_posts if isinstance(item, dict))
    has_nonzero_exposures = any((item.get('exposures') or 0) > 0 for item in sample_posts if isinstance(item, dict))

    if provider == 'playwright_xhs' and not health.get('storage_state_exists', False):
        return {
            'status': 'blocked',
            'summary': '未找到 Playwright 登录态文件，无法做真实账号抓取',
            'issues': ['未找到登录态文件'],
            'suggested_actions': ['先运行 crawler_service/scripts/save_xhs_storage_state.py 保存登录态'],
        }

    if account_count > 0 and post_count > 0:
        if has_nonzero_views and not has_nonzero_exposures:
            return {
                'status': 'partial',
                'summary': f'已成功抓到 {account_count} 个账号、{post_count} 条笔记，阅读量已回流，但曝光量仍未命中',
                'issues': ['账号页状态树或 DOM 里还没有稳定提取到 impression_cnt / exposure_count'],
                'suggested_actions': _unique([
                    '先运行 crawler_service/scripts/debug_xhs_profile.py 检查账号页 HTML 和状态树',
                    '重点查找 impression_cnt、exposure_count、view_count 之外的曝光字段命名',
                    '如果账号页根本不返回曝光量字段，就先接受 exposures=0 的回退口径',
                ]),
            }
        return {
            'status': 'ready',
            'summary': f'已成功抓到 {account_count} 个账号、{post_count} 条笔记',
            'issues': [],
            'suggested_actions': ['可以继续在自动化中心测试账号同步 Worker 回流'],
        }

    if account_count > 0:
        return {
            'status': 'partial',
            'summary': '账号页已抓到，但还没有解析出笔记',
            'issues': ['笔记卡片选择器或页面结构可能需要校准'],
            'suggested_actions': _unique([
                '先运行 crawler_service/scripts/debug_xhs_profile.py 检查账号页截图和 HTML',
                '必要时调整 XHS_POST_CARD_SELECTOR / XHS_POST_TITLE_SELECTOR',
            ]),
        }

    return {
        'status': 'blocked',
        'summary': '账号抓取未返回账号信息',
        'issues': ['账号主页可能未打开成功，或页面结构未命中默认选择器'],
        'suggested_actions': _unique([
            '确认 XHS_PROBE_PROFILE_URL 或 XHS_PROBE_ACCOUNT_HANDLE 是否正确',
            '先运行 crawler_service/scripts/debug_xhs_profile.py 检查账号页截图和 HTML',
        ]),
    }


def build_bundle_diagnosis(summary):
    summary = summary or {}
    trend_diag = build_trend_probe_diagnosis(summary.get('trends') or {})
    account_diag = build_account_probe_diagnosis(summary.get('account_posts') or {})
    statuses = {trend_diag.get('status'), account_diag.get('status')}

    if 'blocked' in statuses:
        status = 'blocked'
        summary_text = '至少有一条 crawler 联调链路仍被阻塞'
    elif 'partial' in statuses:
        status = 'partial'
        summary_text = 'crawler 联调已部分可用，但还需要继续校准'
    else:
        status = 'ready'
        summary_text = '热点和账号两条 crawler 联调链路都已可用'

    suggested_actions = []
    suggested_actions.extend(trend_diag.get('suggested_actions') or [])
    suggested_actions.extend(account_diag.get('suggested_actions') or [])

    return {
        'status': status,
        'summary': summary_text,
        'components': {
            'trends': trend_diag,
            'account_posts': account_diag,
        },
        'suggested_actions': _unique(suggested_actions),
    }
