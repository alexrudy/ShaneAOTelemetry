#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
import numpy as np
from telemetry.cli import parser
from telemetry.models import TelemetryKind, Telemetry, Dataset, TransferFunction, TransferFunctionFit

import matplotlib
# matplotlib.use("TkAgg")
matplotlib.rcParams['text.usetex'] = False

def setup(parser):
    """Set up the argument parser"""
    parser.add_argument("kind", type=str, help="Data kind to periodogram.")

def main():
    """Make transfer functions components."""
    opt = parser(setup)
    
    session = opt.session
    name = "transferfunctionmodel/{0}".format(opt.kind)
    tf_name = "transferfunction/{0}".format(opt.kind)
    kind = session.query(TelemetryKind).filter(TelemetryKind.h5path == name).one()
    print(kind)
    
    t_query = session.query(Dataset.id).join(Telemetry).join(TelemetryKind).filter(TelemetryKind.h5path == name)
    query = session.query(Dataset).filter(Dataset.loop == "closed")
    
    if opt.date is not None:
        t_query = t_query.filter(Dataset.id.in_(opt.query))
        query = query.filter(Dataset.id.in_(opt.query))
    
    print("{0:d} potential target datasets.".format(query.count()))
    
    query = query.filter(Dataset.id.in_(t_query))
    
    print("Generating {0} for {1} datasets.".format(kind.name, query.count()))
    print("{0:d} datasets already have {1}".format(t_query.count(), kind.name))
    iterator = iter(query.all())
    dataset = next(iterator)
    model = dataset.telemetry[name].read()
    params = { pname:getattr(model, pname).value for pname in model.param_names }
    params['gain'] /= dataset.gain
    params['tau'] *= dataset.wfs_rate
    for dataset in iterator:
        model = dataset.telemetry[name].read()
        for pname in params:
            if pname == "gain":
                params[pname] = np.vstack((params[pname], getattr(model, pname).value / dataset.gain))
            elif pname == "tau":
                params[pname] = np.vstack((params[pname], getattr(model, pname).value * dataset.wfs_rate))
            else:
                params[pname] = np.vstack((params[pname], getattr(model, pname).value))
    
    
    params['integrator'] = 1.0 - np.exp(params.pop("ln_c"))
    for pname in params:
        data = params[pname]
        params[pname] = data[data != 0.0]
    
    
    
    import matplotlib.pyplot as plt
    import seaborn
    for parameter in params:
        data = params[parameter]
        plt.figure()
        plt.title(parameter)
        plt.hist(data.flatten(), bins=50)
    plt.show()

if __name__ == '__main__':
    main()