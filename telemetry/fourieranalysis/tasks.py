# -*- coding: utf-8 -*-

from telemetry.models import Dataset, TelemetryKind
from telemetry.application import app
from .models import TransferFunctionPair
from .views import save_transfer_plot, save_periodogram_plot


@app.celery.task(bind=True)
def pair(self, dataset_id):
    """Pair a dataset."""
    dataset = self.session.query(Dataset).filter_by(id=dataset_id).one()
    other = dataset.match()
    if other is None:
        print("Couldn't match {0}".format(dataset))
        return
    pair = self.session.query(TransferFunctionPair).filter(
        TransferFunctionPair.loop_open_id == other.id).filter(
        TransferFunctionPair.loop_closed_id == other.id).one_or_none()
    if pair is None:
        print("Matched {0}".format(dataset))
        print("To {0}".format(other))
        pair = TransferFunctionPair(loop_open=other, loop_closed=dataset)
        self.session.add(pair)
    self.session.commit()
    

@app.celery.task(bind=True)
def periodogram(self, dataset_id, kind, length=1024, options=dict()):
    """Make a periodogram."""
    options.setdefault('half_overlap', False)
    path = "periodogram/{0}".format(kind)
    kind = self.session.query(TelemetryKind).filter(TelemetryKind.h5path == path).one()
    dataset = self.session.query(Dataset).filter_by(id=dataset_id).one()
    tel = kind.generate(dataset, length, **options)
    self.session.add(tel)
    self.session.commit()
    
@app.celery.task(bind=True)
def transferfunction(self, dataset_id, kind):
    """Make a transfer function."""
    path = "transferfunction/{0}".format(kind)
    kind = self.session.query(TelemetryKind).filter(TelemetryKind.h5path == path).one()
    dataset = self.session.query(Dataset).filter_by(id=dataset_id).one()
    tel = kind.generate(dataset)
    self.session.add(tel)
    self.session.commit()
    
@app.celery.task(bind=True)
def transferfunction_plot(self, dataset_id, kind):
    """Make a plot of a transfer function."""
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams['text.usetex'] = False
    import seaborn
    
    path = "transferfunction/{0}".format(kind)
    dataset = self.session.query(Dataset).filter_by(id=dataset_id).one()
    tel = dataset.telemetry[path]
    return save_transfer_plot(tel)

@app.celery.task(bind=True)
def periodoram_plot(self, dataset_id, kind):
    """Periodogram plot."""
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams['text.usetex'] = False
    import seaborn
    
    path = "periodogram/{0}".format(kind)
    dataset = self.session.query(Dataset).filter_by(id=dataset_id).one()
    periodogram = dataset.telemetry[path]
    return save_periodogram_plot(periodogram)
