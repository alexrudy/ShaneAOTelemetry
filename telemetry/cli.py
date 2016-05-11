# -*- coding: utf-8 -*-
from __future__ import absolute_import

"""
Basic command line tools.
"""

import click
import argparse
import datetime
import time
import itertools
from celery import group
from telemetry.models import Dataset, TelemetryKind
from sqlalchemy.sql import between
from astropy.utils.console import ProgressBar

__all__ = ['progress', 'cli']

def progress(resultset):
    """A group result progressbar."""
    with ProgressBar(len(resultset)) as pbar:
        pbar.update(0)
        while not resultset.ready():
            pbar.update(resultset.completed_count())
            time.sleep(0.1)
        pbar.update(resultset.completed_count())
    return
    
@click.group()
def cli():
    pass
    
@cli.command()
def shell():
    """Launch a shell."""
    import IPython
    from .application import app
    from .models import Dataset
    with app.app_context():
        IPython.embed()
    
class CeleryGroupError(click.ClickException):
    """Raised with an error from the celery group."""
    
    def show(self):
        """Show the Celery group error."""
        click.echo(str(self))
        
    
class ClickGroup(object):
    """A click group class"""
    def __init__(self, **kwargs):
        super(ClickGroup, self).__init__()
        self.__dict__.update(kwargs)
    
    @classmethod
    def callback(cls, name):
        """Get an option callback."""
        def callback(ctx, param, value):
            state = ctx.ensure_object(cls)
            setattr(state, name, value)
            return value
        return callback
        
    @classmethod
    def option(cls, *args, **kwargs):
        """Add an option"""
        name = kwargs.pop('name')
        kwargs['callback'] = cls.callback(name)
        kwargs.setdefault('expose_value', False)
        return click.option(*args, **kwargs)
    
    @classmethod
    def argument(cls, *args, **kwargs):
        """Add an argument."""
        name = kwargs.pop('name')
        kwargs['callback'] = cls.callback(name)
        kwargs.setdefault('expose_value', False)
        return click.argument(*args, **kwargs)
        
    @classmethod
    def decorate(cls, func):
        """Decorate a function."""
        pass_progress_group = click.make_pass_decorator(cls, ensure=True)
        return pass_progress_group(func)
    
class CeleryProgressGroup(ClickGroup):
    """A state management for celery progress."""
    def __init__(self, try_one=False, wait=True, limit=None, local=False):
        super(CeleryProgressGroup, self).__init__(try_one=try_one, wait=wait, limit=limit, local=False)
        
    def __call__(self, iterator):
        """Call the progress."""
        if self.limit is not None:
            iterator = itertools.islice(iterator, 0, self.limit)
        g = group(iterator)
        if self.try_one:
            click.echo("Trying a single task:")
            try:
                task = next(iter(g))
            except StopIteration:
                raise CeleryGroupError("No tasks were available.")
            else:
                if self.local:
                    result = task()
                else:
                    result = task.delay().get()
                click.echo("Success! {0}".format(result))
        if self.local:
            r = g()
            return r
        else:
            r = g.delay()
        if self.wait:
            progress(r)
        else:
            click.echo("Tasks started for group {0}".format(r.id))
        return r
        
    @classmethod
    def decorate(cls, func):
        """docstring for decorate"""
        func = cls.option("--try-one/--no-try", default=False,
            name="try_one", help="Try a single value")(func)
        func = cls.option("--limit", type=int, default=None,
            name="limit", help="Limit the number of tasks to process.")(func)
        func = cls.option("--wait/--no-wait", default=True,
            name="wait", help="Wait for tasks to finish.")(func)
        func = cls.option("--local/--remote", default=True, name="local",
            help="Run tasks locally.")(func)
        func = super(CeleryProgressGroup, cls).decorate(func)
        return func

def celery_progress(func):
    """A decorator to add celery progress options to a function."""
    return CeleryProgressGroup.decorate(func)


