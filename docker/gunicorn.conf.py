import multiprocessing
import os


bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
workers = int(os.environ.get('GUNICORN_WORKERS', max(multiprocessing.cpu_count() // 2, 2)))
threads = int(os.environ.get('GUNICORN_THREADS', '4'))
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'gthread')
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '120'))
graceful_timeout = int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', '30'))
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', '5'))
accesslog = '-'
errorlog = '-'
capture_output = True
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
worker_tmp_dir = '/dev/shm'
