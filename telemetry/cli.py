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
import lumberjack
import logging
from celery import group
from telemetry.models import Dataset, TelemetryKind
from sqlalchemy.sql import between
from astropy.utils.console import ProgressBar
from functools import update_wrapper
from .application import app

__all__ = ['progress', 'cli', 'ClickError']

log = logging.getLogger(__name__)

def progress(resultset):
    """A group result progressbar."""
    with ProgressBar(len(resultset)) as pbar:
        pbar.update(0)
        while not resultset.ready():
            pbar.update(sum(int(result.ready()) for result in resultset))
            time.sleep(0.1)
        pbar.update(sum(int(result.ready()) for result in resultset))
    return
    
@click.group()
def cli():
    lumberjack.setup_logging(mode='stream', level=logging.DEBUG)
    click.secho("Connected to {0}".format(app.config['SQLALCHEMY_DATABASE_URI']), fg='blue')
    log.info("Set up logging.")
    
@cli.command()
def shell():
    """Launch a shell."""
    import IPython
    from .application import app
    from .models import Dataset
    with app.app_context():
        IPython.embed()
        
    

def setup_context(f):
    """Set up the context so it can be used to pass argument groups."""
    @click.pass_context
    def new_func(ctx, *args, **kwargs):
        obj = ctx.ensure_object(dict)
        kwargs.update(obj)
        return ctx.invoke(f, **kwargs)
    return update_wrapper(new_func, f)

class ClickError(click.ClickException):
    """Raised with an error from the celery group."""
    
    def show(self):
        """Show the Celery group error."""
        click.echo(str(self))
        
    

class ClickGroup(object):
    """A click group class"""
    
    argument = "group"
    
    def __init__(self, **kwargs):
        super(ClickGroup, self).__init__()
        self.__dict__.update(kwargs)
    
    @classmethod
    def callback(cls, name):
        """Get an option callback."""
        def callback(ctx, param, value):
            state = ctx.ensure_object(dict)
            if cls.argument not in state:
                state[cls.argument] = cls()
            setattr(state[cls.argument], name, value)
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
        return setup_context(func)
    
class CeleryProgressGroup(ClickGroup):
    """A state management for celery progress."""
    
    argument = 'progress'
    
    def __init__(self, try_one=False, wait=True, limit=None, local=False, try_local=False):
        super(CeleryProgressGroup, self).__init__(try_one=try_one, wait=wait, limit=limit, local=False, try_local=try_local, timeout=None)
        
    def __call__(self, iterator):
        """Call the progress."""
        if self.limit is not None:
            click.echo("Limiting to {0:d} items.".format(self.limit))
            iterator = itertools.islice(iterator, 0, self.limit)
        results = []
        iterator = iter(iterator)
        if self.try_one or self.try_local:
            click.echo("Trying a single task:")
            try:
                task = next(iterator)
            except StopIteration:
                click.secho("No tasks were available", fg='red')
                raise ClickError("Empty task list.")
            else:
                click.echo(">>> {0!r}".format(task))
                try:
                    if self.local or self.try_local:
                        result = task()
                    else:
                        result = task.delay()
                    if hasattr(result, 'get'):
                        result = result.get(timeout=self.timeout)
                except Exception:
                    click.secho("Failure!", fg='red')
                    raise
                else:
                    click.echo("{0!r}".format(result))
                    click.secho("Success!", fg="green")
                    results.append(result)
        if self.try_local:
            return results
        g = group(iterator)
        if not len(g.tasks):
            click.secho("No tasks were available", fg='red')
            raise ClickError("Empty task list.")
        if self.local:
            click.echo("Running tasks locally.".format(self.limit))
            for task in g:
                results.append(task())
            click.echo("Results:")
            click.echo("\n".join([repr(result.get()) for result in results]))
            return results
        else:
            r = g.delay()
            try:
                if self.wait:
                    progress(r)
                else:
                    click.echo("Tasks started for group {0}".format(r.id))
            except KeyboardInterrupt:
                click.echo("Tasks will not be revoked.")
                raise
            else:
                click.echo("Completed {:d} tasks: {:d} successes, {:d} failures.".format(
                    sum(int(result.ready()) for result in r),
                    sum(int(result.successful()) for result in r), 
                    sum(int(result.failed()) for result in r)
                ))
            return r
        
    @classmethod
    def decorate(cls, func):
        """docstring for decorate"""
        func = cls.option("--try-one/--no-try-one", default=False,
            name="try_one", help="Try a single task")(func)
        func = cls.option("--limit", type=int, default=None,
            name="limit", help="Limit the number of tasks to process.")(func)
        func = cls.option("--wait/--no-wait", default=True,
            name="wait", help="Wait for tasks to finish.")(func)
        func = cls.option("--local/--remote", default=False, name="local",
            help="Run tasks locally.")(func)
        func = cls.option("--try-local/--no-try-local", default=False, name="try_local", help="Try a single task, locally.")(func)
        func = super(CeleryProgressGroup, cls).decorate(func)
        return func



