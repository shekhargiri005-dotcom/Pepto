import multiprocessing

# Gunicorn configuration file
# https://docs.gunicorn.org/en/stable/settings.html

# The number of worker processes for handling requests.
workers = 2 # Usually multiprocessing.cpu_count() * 2 + 1, but limit to 2 for Render free/starter tiers

# The type of workers to use. Eventlet is required for Flask-SocketIO.
worker_class = 'eventlet'

# The socket to bind.
bind = '0.0.0.0:5000'

# Workers silent for more than this many seconds are killed and restarted.
timeout = 120

# The number of pending connections.
backlog = 2048

# Write access and error info to stdout/stderr
accesslog = '-'
errorlog = '-'
loglevel = 'info'
