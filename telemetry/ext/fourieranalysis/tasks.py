# -*- coding: utf-8 -*-

from telemetry.models import Dataset, TelemetryKind
from telemetry.application import app
from .models import TransferFunctionPair

@app.celery.task(bind=True)
def pair(self, dataset_id):
    """Pair a dataset."""
    dataset = self.session.query(Dataset).filter_by(id=dataset_id).one()
    if dataset.instrument_data.loop != "closed":
        return "Loop wasn't closed"
    other = dataset.instrument_data.match()
    if other is None:
        return "Can't match {0}.".format(dataset)
    pair = self.session.query(TransferFunctionPair).filter(
        TransferFunctionPair.loop_open_id == other.id).filter(
        TransferFunctionPair.loop_closed_id == dataset.id).one_or_none()
    if pair is None:
        pair = TransferFunctionPair(loop_open=other, loop_closed=dataset)
        self.session.add(pair)
    message = "Success, matched to {0}".format(other)
    self.session.commit()
    return message
    

