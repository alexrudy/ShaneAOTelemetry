# -*- coding: utf-8 -*-

import click
from telemetry.cli import cli, CeleryProgressGroup
from telemetry.db import DatasetQuery
from telemetry.application import app
from telemetry.models import Dataset, TelemetryKind, Telemetry
from telemetry.views.cli import plotting_command
from telemetry import tasks as base_tasks
from . import tasks
from .views import periodogram_plot, transferfunction_plot, transferfunction_model_summary, powerspectrum_plot, tf_low_modes

@cli.group()
def fa():
    """Fourier Analysis group."""
    pass


@fa.command()
@CeleryProgressGroup.decorate
def sequence(progress):
    """Sequence datasets."""
    with app.app_context():
        query = app.session.query(Dataset).order_by(Dataset.created)
        click.echo("Sequencing {0:d} datasets.".format(query.count()))
        progress(tasks.pair.si(dataset.id) for dataset in query.all())
        

def generate_pairwise(name, task, parent_name, child_name, **kwargs):
    """Generate a pairwise CLI."""
    
    group = kwargs.pop('group', fa)
    
    @group.command(name=name)
    @click.argument("component", type=str)
    @click.option("--force/--no-force", help="Force regenerate.", default=False)
    @CeleryProgressGroup.decorate
    @DatasetQuery.decorate
    def _command(datasetquery, progress, component, force):
        """Generate {0} from pairwise datasets.""".format(child_name)
        with app.app_context():
            child = TelemetryKind.require(app.session, child_name.format(component))
            parent = TelemetryKind.require(app.session, parent_name.format(component))
            if not hasattr(child, 'generate'):
                raise click.BadParameter("{0} does not appear to have a .generate() method.".format(component))
            
            e_query = app.session.query(Dataset.id).join(Telemetry).join(TelemetryKind).filter(TelemetryKind.id == parent.id)
            t_query = app.session.query(Dataset.id).join(Telemetry).join(TelemetryKind).filter(TelemetryKind.id == child.id)
            query = datasetquery(app.session).filter(Dataset.id.in_(e_query)).join(Dataset.pairs)
            
            if not e_query.count():
                click.echo(e_query)
                click.echo("No datasets have {0}. {1}".format(parent, parent.id))
            click.echo("{0:d} potential target datasets.".format(query.count()))
        
            if not force:
                query = query.filter(Dataset.id.notin_(t_query))
            
            kwargs['force'] = force
            click.echo("Generating {0} for {1} datasets.".format(child.name, query.count()))
            click.echo("{0:d} datasets already have {1}".format(t_query.count(), child.name))
            progress(task.si(dataset.id, child.id, **kwargs) for dataset in query.all())
    return _command

tf = generate_pairwise('tf', base_tasks.generate, "periodogram/{0}", "transferfunction/{0}")
tffit = generate_pairwise('tffit', base_tasks.generate, "transferfunction/{0}", "transferfunctionmodel/{0}")

@fa.group()
def plot():
    """Plotting for the Fourier Analysis module"""
    pass

pgplot = plotting_command('periodogram', periodogram_plot, group=plot, component_name_transform="periodogram/{0}".format)
psplot = plotting_command('ps', powerspectrum_plot, group=plot, component_name_transform="periodogram/{0}".format)
tfplot = plotting_command('tf', transferfunction_plot, group=plot, component_name_transform="transferfunction/{0}".format)
tffitplot = plotting_command('tffit', transferfunction_model_summary, group=plot, component_name_transform="transferfunctionmodel/{0}".format)
tflowmodes = plotting_command('tflow', tf_low_modes, group=plot, component_name_transform="transferfunction/{0}".format)
