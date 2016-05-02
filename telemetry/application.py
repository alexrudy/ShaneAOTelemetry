# -*- coding: utf-8 -*-
from __future__ import absolute_import
from flask import Flask
from celery import Celery
import sqlalchemy
from sqlalchemy.orm import scoped_session, sessionmaker
import os, socket

def prepare_celery(app):
    """Set up celery for this application."""
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        """A task which maintains an SQLAlchemy database session."""
        abstract = True
        _session = None
    
        @property
        def session(self):
            """Database session"""
            if self._session is None:
                self._session = scoped_session(sessionmaker(bind=app.engine))
            return self._session
        
        def after_return(self, *args, **kwargs):
            if self._session is not None:
                self._session.remove()
            super(ContextTask, self).after_return(*args, **kwargs)
        
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return super(ContextTask, self).__call__(*args, **kwargs)
        
    
    celery.Task = ContextTask
    return celery

def prepare_sqlalchemy(app):
    """Prepare SQLAlchemy"""
    from .models.base import Base
    
    app.config.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite://')
    app.config.setdefault('SQLALCHEMY_ECHO', False)
    app.config.setdefault('SQLALCHEMY_RECORD_QUERIES', None)
    app.config.setdefault('SQLALCHEMY_POOL_SIZE', None)
    app.config.setdefault('SQLALCHEMY_POOL_TIMEOUT', None)
    app.config.setdefault('SQLALCHEMY_POOL_RECYCLE', None)
    app.config.setdefault('SQLALCHEMY_MAX_OVERFLOW', None)
    app.config.setdefault('SQLALCHEMY_COMMIT_ON_TEARDOWN', False)
    
    @app.teardown_appcontext
    def shutdown(response_or_exc):
        """Shutdown the database connection after requests."""
        if app.config.get('SQLALCHEMY_COMMIT_ON_TEARDOWN', False):
            if response_or_exc is None:
                app.session.commit()
        app.session.remove()
        return response_or_exc
    
    app.metadata = Base.metadata
    return app.metadata
    

def prepare_entrypoints(app):
    """Prepare entrypoints."""
    import pkg_resources
    for entry_point in app.config['TELEMETRY_ENTRYPOINTS']:
        ep = pkg_resources.EntryPoint.parse(entry_point, dist=None)
        setup_func = ep.load(require=False)
        setup_func(app)

class TelemetryFlask(Flask):
    """A custom flask application."""
    
    _engine = None
    @property
    def engine(self):
        """Get the SQLAlchemy Engine"""
        if self._engine is None:
            uri = self.config["SQLALCHEMY_DATABASE_URI"]
            options = {}
            options['echo'] = self.config["SQLALCHEMY_ECHO"]
            self._engine = sqlalchemy.create_engine(uri, **options)
        return self._engine
        
    def create_all(self):
        """Create all DB tables."""
        self.metadata.create_all(self.engine)
    
    _session = None
    @property
    def session(self):
        """docstring for session"""
        if self._session is None:
            self._session = scoped_session(sessionmaker(bind=self.engine))
        return self._session
    
    _celery = None
    @property
    def celery(self):
        """Make the celery applicaiton."""
        if self._celery is None:
            self._celery = prepare_celery(self)
        return self._celery
    
def get_instance_path():
    """Get the instance path."""
    hostname = socket.gethostname()
    packagedir = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.abspath(os.path.join(packagedir, hostname))
    
app = TelemetryFlask("telemetry", instance_path=get_instance_path(), instance_relative_config=True)
app.config.from_object("telemetry.default_config")
app.config.from_pyfile("telemetry.cfg", silent=True)
metadata = prepare_sqlalchemy(app)
prepare_entrypoints(app)