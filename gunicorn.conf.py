# gunicorn.conf.py

# A single synchronous worker is fastest for webhook/API environments
workers = 1 

# Bind to the port Render provides
bind = '0.0.0.0:8000' 

# Set a slightly longer timeout just in case, though 30 is the default.
# Render's deploy timeout is 60s, this is for request processing.
timeout = 30