#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
import numpy as np
from telemetry.cli import parser
from telemetry.application import app
from telemetry.models import TelemetryKind, Telemetry, Dataset
from telemetry.fourieranalysis.models import TransferFunction, TransferFunctionFit
from astropy.utils.console import ProgressBar
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams['text.usetex'] = False

def setup(parser):
    """Set up the argument parser"""
    parser.add_argument("kind", type=str, help="Data kind to periodogram.")

def read_model(params, model, dataset):
    """Read model"""
    for pname in model.param_names:
        if pname == "gain":
            params[pname] = np.vstack((params[pname], getattr(model, pname).value))
            params['gain performance'] = np.vstack((params['gain performance'], dataset.gain / getattr(model, pname).value))
        elif pname == "tau":
            params[pname] = np.vstack((params[pname], getattr(model, pname).value * dataset.wfs_rate))
            params['frame delay'] = np.vstack((params['frame delay'], getattr(model, pname).value * dataset.wfs_rate))
        else:
            params[pname] = np.vstack((params[pname], getattr(model, pname).value))

def main():
    """Make transfer functions components."""
    opt = parser(setup)
    
    with app.app_context():
        session = app.session
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
        iterator = ProgressBar(query.all())
        dataset = next(iterator)
        model = dataset.telemetry[name].read()
        params = { pname:getattr(model, pname).value for pname in model.param_names }
        params['gain performance'] = dataset.gain / model.gain.value
        params['frame delay'] = params['tau'] * dataset.wfs_rate
        
        for dataset in iterator:
            model = dataset.telemetry[name].read()
            read_model(params, model, dataset)
        
        params.pop('rate')
        params['integrator'] = 1.0 - np.exp(params["ln_c"])
        params['ln_gain_gain'] = np.log(params['gain performance'])
        keep = (params['gain'].flatten() > 0.01) & (np.isfinite(params['gain performance'].flatten())) & (params['gain performance'].flatten() < 100)
        keep &= (params['tau'].flatten() != 0.0)
        for pname in params:
            data = params[pname].flatten()
            print(pname, keep.shape, data.shape)
            params[pname] = data[keep]
        
        import matplotlib.pyplot as plt
        import seaborn
        for parameter in params:
            data = params[parameter]
            plt.figure()
            plt.title(parameter)
            if parameter.startswith("ln"):
                data = np.exp(data.flatten())
                plt.hist(data, bins=np.logspace(data.min(), data.max(), 50))
                plt.xscale('log')
            else:
                plt.hist(data.flatten(), bins=50)
            plt.savefig("{}.png".format(parameter))

if __name__ == '__main__':
    main()