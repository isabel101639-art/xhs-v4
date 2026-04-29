import argparse
import json
import os
import socket
import ssl
import sys
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from release_manifest import build_release_manifest_payload


DEFAULT_COPY_PROMPT = '请用更像真人的小红书口语风，写一句关于肝健康的开头。'
DEFAULT_IMAGE_PROMPT = '生成一张适合小红书医疗科普封面的测试图片，画面简洁，标题区留白。'
LOCAL_RELEASE_MANIFEST = build_release_manifest_payload(include_generated_at=False)
EXPECTED_RELEASE_FEATURES = [
    key for key, enabled in (LOCAL_RELEASE_MANIFEST.get('release_features') or {}).items()
    if enabled
]
MANIFEST_UI_PATHS = {
    'automation_center': '/automation_center',
    'data_analysis': '/data_analysis',
}


def _fail(message):
    raise AssertionError(message)


def _print_ok(label, detail):
    print(f'[OK] {label}: {detail}')


def _record_result(summary, label, status, detail=''):
    summary['results'].append({
        'label': label,
        'status': status,
        'detail': str(detail or ''),
    })


def _write_summary_json(path, summary):
    if not path:
        return
    target = os.path.abspath(path)
    parent = os.path.dirname(target)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(target, 'w', encoding='utf-8') as fp:
        json.dump(summary, fp, ensure_ascii=False, indent=2)


def _run_check(summary, label, fn, *, soft=False):
    try:
        result = fn()
        _record_result(summary, label, 'ok')
        return result
    except AssertionError as exc:
        if soft:
            _record_result(summary, label, 'warn', str(exc))
            print(f'[WARN] {label}: {exc}')
            return None
        _record_result(summary, label, 'fail', str(exc))
        raise


def _build_opener(insecure=False):
    cookie_jar = CookieJar()
    handlers = [HTTPCookieProcessor(cookie_jar)]
    if insecure:
        handlers.append(HTTPSHandler(context=ssl._create_unverified_context()))
    return build_opener(*handlers)


def _request(opener, method, url, *, data=None, headers=None, timeout=30):
    payload = None
    request_headers = dict(headers or {})
    if data is not None:
        if isinstance(data, bytes):
            payload = data
        else:
            payload = str(data).encode('utf-8')
    request = Request(url, data=payload, headers=request_headers, method=method.upper())
    try:
        response = opener.open(request, timeout=timeout)
        body = response.read().decode('utf-8', errors='replace')
        return response.getcode(), body, response.geturl()
    except HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        return exc.code, body, exc.geturl()
    except URLError as exc:
        _fail(f'{url} 请求失败：{exc}')
    except socket.timeout:
        _fail(f'{url} 请求超时，timeout={timeout}s')


def _get_json(opener, method, url, *, data=None, headers=None, timeout=30):
    status, body, final_url = _request(opener, method, url, data=data, headers=headers, timeout=timeout)
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        _fail(f'{url} 返回不是合法 JSON：{exc} ｜ body={body[:300]}')
    return status, parsed, final_url


def _login(opener, base_url, username, password, timeout):
    login_url = urljoin(base_url, '/admin/login')
    form_data = urlencode({
        'username': username,
        'password': password,
    }).encode('utf-8')
    status, body, final_url = _request(
        opener,
        'POST',
        login_url,
        data=form_data,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=timeout,
    )
    if status != 200:
        _fail(f'admin login 失败，http={status}')
    if '用户名或密码错误' in body:
        _fail('admin login 失败，用户名或密码错误')
    if '/admin' not in final_url:
        _fail(f'admin login 未跳转到后台首页，final_url={final_url}')
    _print_ok('admin_login', final_url)


def _check_healthz(opener, base_url, timeout):
    status, data, _ = _get_json(opener, 'GET', urljoin(base_url, '/healthz'), timeout=timeout)
    if status != 200:
        _fail(f'healthz http={status}')
    if not data.get('success') or data.get('status') != 'ok':
        _fail(f'healthz 异常：{json.dumps(data, ensure_ascii=False)}')
    _print_ok('healthz', json.dumps({
        'status': data.get('status'),
        'database': data.get('database'),
    }, ensure_ascii=False))


def _check_page_contains(opener, base_url, path, tokens, label, timeout):
    status, body, final_url = _request(opener, 'GET', urljoin(base_url, path), timeout=timeout)
    if status != 200:
        _fail(f'{label} http={status}')
    missing = [token for token in tokens if token not in body]
    if missing:
        _fail(f'{label} 缺少关键标记：{missing} ｜ final_url={final_url}')
    _print_ok(label, final_url)


def _check_manifest_backed_ui_pages(opener, base_url, manifest, timeout):
    ui_markers = manifest.get('ui_markers') or {}
    for page_key, path in MANIFEST_UI_PATHS.items():
        tokens = list(ui_markers.get(page_key) or [])
        tokens.extend([
            'xhs-release-version',
            (manifest.get('release_version') or '').strip(),
            (manifest.get('release_fingerprint') or '').strip(),
        ])
        deduped_tokens = []
        seen = set()
        for token in tokens:
            normalized = str(token or '').strip()
            if not normalized or normalized in seen:
                continue
            deduped_tokens.append(normalized)
            seen.add(normalized)
        _check_page_contains(opener, base_url, path, deduped_tokens, f'{page_key}_page', timeout)


def _check_release_manifest(opener, base_url, timeout):
    status, data, _ = _get_json(opener, 'GET', urljoin(base_url, '/api/admin/release-manifest'), timeout=timeout)
    if status != 200 or not data.get('success'):
        _fail(f'release-manifest 失败：http={status} data={json.dumps(data, ensure_ascii=False)}')
    release_version = (data.get('release_version') or '').strip()
    if not release_version:
        _fail('release-manifest 缺少 release_version')
    expected_release_version = (LOCAL_RELEASE_MANIFEST.get('release_version') or '').strip()
    if expected_release_version and release_version != expected_release_version:
        _fail(f'release-manifest 版本不匹配：expected={expected_release_version} actual={release_version}')
    actual_fingerprint = (data.get('release_fingerprint') or '').strip()
    expected_release_fingerprint = (LOCAL_RELEASE_MANIFEST.get('release_fingerprint') or '').strip()
    if expected_release_fingerprint and actual_fingerprint != expected_release_fingerprint:
        _fail(f'release-manifest 指纹不匹配：expected={expected_release_fingerprint} actual={actual_fingerprint}')
    features = data.get('release_features') or {}
    missing = [key for key in EXPECTED_RELEASE_FEATURES if not features.get(key)]
    if missing:
        _fail(f'release-manifest 缺少关键能力：{missing}')
    _print_ok('release_manifest', json.dumps({
        'release_version': release_version,
        'release_fingerprint': data.get('release_fingerprint'),
    }, ensure_ascii=False))
    return data


def _warn_release_manifest(opener, base_url, timeout):
    try:
        return _check_release_manifest(opener, base_url, timeout)
    except AssertionError as exc:
        print(f'[WARN] release_manifest: {exc}')
        return None


def _check_preview(opener, base_url, timeout):
    status, data, _ = _get_json(opener, 'GET', urljoin(base_url, '/api/admin/automation-config/preview'), timeout=timeout)
    if status != 200 or not data.get('success'):
        _fail(f'automation-config preview 失败：http={status} data={json.dumps(data, ensure_ascii=False)}')
    copywriter_preview = data.get('copywriter_preview') or {}
    image_request_preview = data.get('image_request_preview') or {}
    if not copywriter_preview.get('model'):
        _fail('automation-config preview 缺少 copywriter model')
    if not image_request_preview.get('prompt'):
        _fail('automation-config preview 缺少 image prompt preview')
    _print_ok('automation_config_preview', json.dumps({
        'copywriter_model': copywriter_preview.get('model'),
        'copywriter_provider': copywriter_preview.get('provider'),
        'image_provider': ((data.get('capabilities') or {}).get('image_provider_name') or ''),
    }, ensure_ascii=False))


def _check_runtime_diagnostics(opener, base_url, timeout):
    status, data, _ = _get_json(
        opener,
        'GET',
        urljoin(base_url, '/api/admin/runtime-diagnostics'),
        timeout=max(timeout, 90),
    )
    if status != 200 or not data.get('success'):
        _fail(f'runtime-diagnostics 失败：http={status} data={json.dumps(data, ensure_ascii=False)}')
    copywriter_health = data.get('copywriter_health') or {}
    image_health = data.get('image_health') or {}
    if not copywriter_health.get('enabled'):
        _fail('runtime-diagnostics 显示文案模型未启用')
    if not image_health.get('enabled'):
        _fail('runtime-diagnostics 显示图片模型未启用')
    _print_ok('runtime_diagnostics', json.dumps({
        'copywriter_ok': copywriter_health.get('ok'),
        'copywriter_model': ((data.get('copywriter') or {}).get('copywriter_model') or ''),
        'image_ok': image_health.get('ok'),
        'image_provider': ((data.get('capabilities') or {}).get('image_provider_name') or ''),
    }, ensure_ascii=False))


def _warn_runtime_diagnostics(opener, base_url, timeout):
    try:
        _check_runtime_diagnostics(opener, base_url, timeout)
    except AssertionError as exc:
        print(f'[WARN] runtime_diagnostics: {exc}')


def _check_copywriter_ping(opener, base_url, timeout, prompt):
    request_timeout = max(timeout + 30, 60)
    last_status = None
    last_data = None
    for attempt in range(1, 3):
        status, data, _ = _get_json(
            opener,
            'POST',
            urljoin(base_url, '/api/jobs/copywriter/ping'),
            data=json.dumps({
                'wait_seconds': min(max(timeout, 10), 40),
                'prompt_text': prompt,
            }),
            headers={'Content-Type': 'application/json'},
            timeout=request_timeout,
        )
        last_status = status
        last_data = data
        if status == 200 and data.get('success'):
            response_preview = data.get('response_preview') or {}
            if (response_preview.get('text') or '').strip():
                _print_ok('copywriter_ping', json.dumps({
                    'provider': data.get('provider'),
                    'used_model': response_preview.get('used_model'),
                    'thinking_mode': ((data.get('request_preview') or {}).get('thinking_mode')),
                    'attempt': attempt,
                }, ensure_ascii=False))
                return
    _fail(f'copywriter ping 失败：http={last_status} data={json.dumps(last_data, ensure_ascii=False)}')


def _check_image_ping(opener, base_url, timeout, prompt):
    request_timeout = max(timeout + 20, 45)
    status, data, _ = _get_json(
        opener,
        'POST',
        urljoin(base_url, '/api/jobs/assets/ping'),
        data=json.dumps({
            'wait_seconds': min(max(timeout, 15), 45),
            'prompt_text': prompt,
            'title_hint': '上线验活图片',
            'image_count': 1,
        }),
        headers={'Content-Type': 'application/json'},
        timeout=request_timeout,
    )
    if status != 200 or not data.get('success'):
        _fail(f'image ping 失败：http={status} data={json.dumps(data, ensure_ascii=False)}')
    preview_items = data.get('normalized_preview') or []
    if not preview_items:
        _fail('image ping 未返回标准化图片预览')
    preview_url = preview_items[0].get('preview_url') or preview_items[0].get('url') or ''
    if not preview_url:
        _fail('image ping 未返回图片地址')
    _print_ok('image_ping', json.dumps({
        'provider': data.get('provider'),
        'preview_url': preview_url,
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description='上线后快速验活脚本')
    parser.add_argument('--base-url', default=os.environ.get('XHS_BASE_URL', '').strip(), help='站点根地址，如 https://furui-xhs-v4.zeabur.app')
    parser.add_argument('--username', default=os.environ.get('XHS_ADMIN_USERNAME', '').strip(), help='后台账号')
    parser.add_argument('--password', default=os.environ.get('XHS_ADMIN_PASSWORD', '').strip(), help='后台密码')
    parser.add_argument('--timeout', type=int, default=int(os.environ.get('XHS_CHECK_TIMEOUT', '30') or '30'), help='单次请求超时秒数')
    parser.add_argument('--copy-prompt', default=os.environ.get('XHS_COPY_PROMPT', DEFAULT_COPY_PROMPT), help='文案联调用 prompt')
    parser.add_argument('--image-prompt', default=os.environ.get('XHS_IMAGE_PROMPT', DEFAULT_IMAGE_PROMPT), help='图片联调用 prompt')
    parser.add_argument('--insecure', action='store_true', help='跳过 HTTPS 证书校验')
    parser.add_argument('--skip-ui-checks', action='store_true', help='跳过 automation_center / data_analysis 页面标记校验')
    parser.add_argument('--require-current-release', action='store_true', help='即使跳过 UI 校验，也要求线上 release-manifest 必须匹配当前本地版本')
    parser.add_argument('--manifest-only', action='store_true', help='只检查 healthz、登录、release-manifest 和页面版本标记，不跑模型联调')
    parser.add_argument('--summary-json', default='', help='把检查结果写到指定 JSON 文件')
    args = parser.parse_args()

    if not args.base_url:
        _fail('缺少 --base-url 或环境变量 XHS_BASE_URL')
    if not args.username:
        _fail('缺少 --username 或环境变量 XHS_ADMIN_USERNAME')
    if not args.password:
        _fail('缺少 --password 或环境变量 XHS_ADMIN_PASSWORD')

    opener = _build_opener(insecure=args.insecure)
    base_url = args.base_url.rstrip('/')
    summary = {
        'base_url': base_url,
        'local_release_version': LOCAL_RELEASE_MANIFEST.get('release_version'),
        'local_release_fingerprint': LOCAL_RELEASE_MANIFEST.get('release_fingerprint'),
        'local_release_commit_sha': LOCAL_RELEASE_MANIFEST.get('release_commit_sha'),
        'mode': {
            'skip_ui_checks': bool(args.skip_ui_checks),
            'require_current_release': bool(args.require_current_release),
            'manifest_only': bool(args.manifest_only),
            'insecure': bool(args.insecure),
        },
        'results': [],
    }
    try:
        _run_check(summary, 'healthz', lambda: _check_healthz(opener, base_url, args.timeout))
        _run_check(summary, 'admin_login', lambda: _login(opener, base_url, args.username, args.password, args.timeout))
        if args.skip_ui_checks:
            if args.require_current_release:
                _run_check(summary, 'release_manifest', lambda: _check_release_manifest(opener, base_url, args.timeout))
            else:
                _run_check(summary, 'release_manifest', lambda: _check_release_manifest(opener, base_url, args.timeout), soft=True)
            print('[SKIP] automation_center_page: 已跳过 UI 标记校验')
            print('[SKIP] data_analysis_page: 已跳过 UI 标记校验')
            _record_result(summary, 'automation_center_page', 'skipped', '已跳过 UI 标记校验')
            _record_result(summary, 'data_analysis_page', 'skipped', '已跳过 UI 标记校验')
            if args.manifest_only:
                summary['overall_status'] = 'ok'
                _write_summary_json(args.summary_json, summary)
                print('Post deploy manifest-only check passed.')
                return
            _run_check(summary, 'automation_config_preview', lambda: _check_preview(opener, base_url, args.timeout))
            _run_check(summary, 'runtime_diagnostics', lambda: _check_runtime_diagnostics(opener, base_url, args.timeout), soft=True)
        else:
            manifest = _run_check(summary, 'release_manifest', lambda: _check_release_manifest(opener, base_url, args.timeout))
            _run_check(summary, 'ui_pages', lambda: _check_manifest_backed_ui_pages(opener, base_url, manifest, args.timeout))
            if args.manifest_only:
                summary['overall_status'] = 'ok'
                _write_summary_json(args.summary_json, summary)
                print('Post deploy manifest-only check passed.')
                return
            _run_check(summary, 'automation_config_preview', lambda: _check_preview(opener, base_url, args.timeout))
            _run_check(summary, 'runtime_diagnostics', lambda: _check_runtime_diagnostics(opener, base_url, args.timeout))
        if args.manifest_only:
            summary['overall_status'] = 'ok'
            _write_summary_json(args.summary_json, summary)
            print('Post deploy manifest-only check passed.')
            return
        _run_check(summary, 'copywriter_ping', lambda: _check_copywriter_ping(opener, base_url, args.timeout, args.copy_prompt))
        _run_check(summary, 'image_ping', lambda: _check_image_ping(opener, base_url, args.timeout, args.image_prompt))
        summary['overall_status'] = 'ok'
        _write_summary_json(args.summary_json, summary)
        print('Post deploy check passed.')
    except AssertionError as exc:
        summary['overall_status'] = 'fail'
        summary['error'] = str(exc)
        _write_summary_json(args.summary_json, summary)
        raise


if __name__ == '__main__':
    try:
        main()
    except AssertionError as exc:
        print(f'[FAIL] {exc}')
        sys.exit(1)
