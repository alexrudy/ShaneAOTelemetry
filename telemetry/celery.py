# -*- coding: utf-8 -*-
from __future__ import absolute_import
from .application import app
from .cli import cli
import click
import os
import subprocess
celery = app.celery
del app

def is_available():
    """Is celery available"""
    from celery.task.control import inspect
    try:
        insp = inspect()
        d = insp.stats()
    except IOError as e:
        return False
    except ImportError as e:
        print(e)
        return False
    else:
        return True
    
@cli.group(name='celery')
def cgroup():
    """control the celery instance."""
    pass

@cgroup.command()
def check():
    """Check celery statistics"""
    from celery.task.control import inspect
    try:
        insp = inspect()
        d = insp.stats()
    except IOError as e:
        click.echo("{0:s}: {1!s}".format(click.style("IOError", fg='red'),e))
        return
    except ImportError as e:
        click.echo("{0:s}: {1!s}".format(click.style("ImportError", fg='red'),e))
        return False
    else:
        if d is None:
            click.secho("NO WORKERS FOUND", fg='red')
            return 1
        for worker, v in d.items():
            click.secho("{0:s}:".format(worker), fg='green')
            click.echo("  pid: {pid:d}".format(**v))
            click.echo("  processes: {:s}".format(",".join("{:d}".format(p) for p in v['pool']['processes'])))
        return 0
    
@cgroup.command()
@click.option("-n", default=2, type=int, help="Number of workers.")
def start(n):
    """start the celery queues"""
    #     celery -A telemetry.celery multi restart 2 -linfo --pidfile=celery/run/%n.pid --logfile=celery/log/%n.log -c 2
    from .application import app
    
    celery_path = os.path.expanduser(os.path.join(app.config['CELERY_DIRECTORY_ROOT'], 'celery'))
    subprocess.check_call(['celery', '-A', __name__, 'multi', 'restart', '{:d}'.format(n),
                           '-linfo', '--pidfile={path:s}/run/%n.pid'.format(path=celery_path), 
                           '--logfile={path:s}/log/%n.log'.format(path=celery_path), '-c', '2'])

@cgroup.command()
@click.option("-n", default=1, type=int, help="Number of workers.")
def start_movie(n):
    """docstring for start_movie"""
    # celery -A telemetry.celery worker -lINFO --concurrency=1 -n movies.%h -Q movies
    from .application import app
    
    celery_path = os.path.expanduser(os.path.join(app.config['CELERY_DIRECTORY_ROOT'], 'celery'))
    subprocess.check_call(['celery', '-A', __name__, 'worker', '--concurrency={:d}'.format(n),
                           '-linfo', '-n', 'movies.%h', '-Q', 'movies',
                           '--pidfile={path:s}/run/%n.pid'.format(path=celery_path), 
                           '--logfile={path:s}/log/%n.log'.format(path=celery_path)])

@cgroup.command()
@click.option("-n", default=2, type=int, help="Number of workers.")
def stop(n):
    """Stop the celery queues"""
    from .application import app
    
    # celery -A telemetry.celery multi stop 2 --pidfile=celery/run/%n.pid
    celery_path = os.path.expanduser(os.path.join(app.config['CELERY_DIRECTORY_ROOT'], 'celery'))
    subprocess.check_call(['celery', '-A', __name__, 'multi', 'stop', '{:d}'.format(n),
                           '--pidfile={path:s}/run/%n.pid'.format(path=celery_path)])
                    