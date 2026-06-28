from app import create_app
from app.extensions import celery

# Create a Flask app instance to wrap the celery context
flask_app = create_app()

class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)

celery.Task = ContextTask
