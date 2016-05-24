# -*- coding: utf-8 -*-
from __future__ import absolute_import
from .application import app
from .cli import cli
import click
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
    """docstring for cgroup"""
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
        for worker, v in d.items():
            click.secho("{0:s}:".format(worker), fg='green')
            click.echo("  pid: {pid:d}".format(**v))
            click.echo("  processes: {:s}".format(",".join("{:d}".format(p) for p in v['pool']['processes'])))
        return True