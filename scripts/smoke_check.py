import os
import sys


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


from app import app, init_db


def main():
    init_db()
    client = app.test_client()

    endpoints = [
        ('healthz', '/healthz'),
        ('home', '/'),
        ('activity_list', '/activity'),
        ('data_analysis', '/data_analysis'),
        ('admin_login', '/admin/login'),
    ]
    for label, path in endpoints:
        res = client.get(path)
        print(label, res.status_code)


if __name__ == '__main__':
    main()
