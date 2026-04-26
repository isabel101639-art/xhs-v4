import argparse
import os
import subprocess
import sys


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(step_label, command):
    print(f'==> {step_label}', flush=True)
    print(' '.join(command), flush=True)
    completed = subprocess.run(command, cwd=ROOT_DIR)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main():
    parser = argparse.ArgumentParser(description='发版前后统一检查入口')
    parser.add_argument('--skip-local', action='store_true', help='跳过本地 py_compile 和 smoke')
    parser.add_argument('--base-url', default=os.environ.get('XHS_BASE_URL', '').strip(), help='线上站点地址；填写后会自动跑 post_deploy_check')
    parser.add_argument('--username', default=os.environ.get('XHS_ADMIN_USERNAME', '').strip(), help='后台账号')
    parser.add_argument('--password', default=os.environ.get('XHS_ADMIN_PASSWORD', '').strip(), help='后台密码')
    parser.add_argument('--insecure', action='store_true', help='透传给 post_deploy_check，跳过证书校验')
    parser.add_argument('--skip-ui-checks', action='store_true', help='透传给 post_deploy_check，跳过前端标记校验')
    parser.add_argument('--require-current-release', action='store_true', help='透传给 post_deploy_check，即使跳过 UI 校验也要求线上已是当前版本')
    parser.add_argument('--manifest-only', action='store_true', help='透传给 post_deploy_check，只做快检，不跑模型联调')
    parser.add_argument('--summary-json', default='', help='透传给 post_deploy_check，把检查结果写到指定 JSON 文件')
    parser.add_argument('--timeout', type=int, default=int(os.environ.get('XHS_CHECK_TIMEOUT', '30') or '30'), help='透传给 post_deploy_check')
    args = parser.parse_args()

    python_bin = sys.executable or 'python3'

    if not args.skip_local:
        _run(
            'py_compile',
            [
                python_bin,
                '-m',
                'py_compile',
                'app.py',
                'automation_dashboard_routes.py',
                'automation_hotwords.py',
                'public_routes.py',
                'release_manifest.py',
                'scripts/smoke_check.py',
                'scripts/post_deploy_check.py',
                'scripts/release_gate.py',
            ],
        )
        _run('smoke_check', [python_bin, 'scripts/smoke_check.py'])

    if args.base_url:
        if not args.username:
            raise SystemExit('缺少 --username 或环境变量 XHS_ADMIN_USERNAME')
        if not args.password:
            raise SystemExit('缺少 --password 或环境变量 XHS_ADMIN_PASSWORD')
        post_command = [
            python_bin,
            'scripts/post_deploy_check.py',
            '--base-url',
            args.base_url,
            '--username',
            args.username,
            '--password',
            args.password,
            '--timeout',
            str(args.timeout),
        ]
        if args.insecure:
            post_command.append('--insecure')
        if args.skip_ui_checks:
            post_command.append('--skip-ui-checks')
        if args.require_current_release:
            post_command.append('--require-current-release')
        if args.manifest_only:
            post_command.append('--manifest-only')
        if args.summary_json:
            post_command.extend(['--summary-json', args.summary_json])
        _run('post_deploy_check', post_command)
    else:
        print('==> post_deploy_check', flush=True)
        print('未提供 --base-url，已跳过线上验活。', flush=True)

    print('Release gate passed.', flush=True)


if __name__ == '__main__':
    main()
