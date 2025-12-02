# gunicorn.conf.py (UPDATED)

worker_class = 'uvicorn.workers.UvicornWorker'
workers = 1
bind = '0.0.0.0:10000'
timeout = 120
keepalive = 5