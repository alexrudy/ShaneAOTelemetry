#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Make various components.
"""

import argparse, sys

__tasks = {}
def task(func):
    __tasks[func.__name__] = func
    return func
    
def main():
    """Set up the argument parser."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("task", choices=__tasks.keys())
    opt, args = parser.parse_known_args()
    
    subparser = argparse.ArgumentParser(sys.argv[0] + " {0}".format(opt.task))
    
    __tasks[opt.task](subparser, args)
    
@task
def periodograms(parser, args):
    """Main function for parsing."""
    parser.add_argument("-f", "--force", action='store_true', help="Force creation of periodograms")
    parser.add_argument("-l", "--length", type=int, help="Periodogram length", default=1024)
    parser.add_argument("-s", "--suppress-static", action='store_true', help="Suppress static in PSDs")
    parser.add_argument("-k", "--kind", choices=set("sx sy coefficients".split()), default="coefficients")
    opt = parser.parse_args(args)
    
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Periodogram, PeriodogramStack, Sequence
    session = Session()
    from astropy.utils.console import ProgressBar
    
    n_telemetry = 0
    
    print("Generating periodograms...")
    for sequence in ProgressBar(session.query(Sequence).all()):
        
        if opt.force or not sequence.periodograms:
            pgram = PeriodogramStack.from_sequence(sequence, opt.kind, opt.length, suppress_static=opt.suppress_static)
            session.add(pgram)
            n_telemetry += 1
    session.commit()
    print("Created {0:d} periodograms.".format(n_telemetry))
    
@task
def tf(parser, args):
    """Create transfer functions."""
    parser.add_argument("-k", "--kind", choices=set("sx sy coefficients".split()), default="coefficients")
    opt = parser.parse_args(args)
    
    from telemetry.models import Dataset, PeriodogramStack, Sequence, TransferFunction
    from telemetry import connect
    Session = connect()
    session = Session()
    from astropy.utils.console import ProgressBar
    
    for sequence in ProgressBar(session.query(Sequence).filter(Sequence.pair_id != None, Sequence.loop == "closed").all()):
        if not sequence.transferfunctions:
            tf = TransferFunction.from_periodogram(sequence.periodograms[opt.kind])
            session.add(tf)
    session.commit()
    
@task
def tffit(parser, args):
    """Make a transfer function fits."""
    parser.add_argument("kind", choices=set("sx sy coefficients".split()))
    parser.add_argument("--tau", help="guess for the delay (in s)", type=float, default=0.05)
    opt = parser.parse_args(args)
    
    from telemetry import connect
    from telemetry.models import TransferFunction, TransferFunctionModel
    Session = connect()
    from telemetry.algorithms.transfer.model import expected_model, fit_model, fit_all_models
    
    session = Session()
    from astropy.utils.console import ProgressBar
    
    for tf in session.query(TransferFunction).filter(TransferFunction.kind == opt.kind).all():
        model = fit_all_models(tf, opt.tau)
        tfm = TransferFunctionModel.from_model(tf, model)
        session.add(tfm)
        session.commit()
    
@task
def slopes(parser, args):
    """Main function for parsing."""
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Slopes
    from astropy.utils.console import ProgressBar
    
    session = Session()
    
    n_telemetry = 0
    print("Generating slopes...")
    
    for dataset in ProgressBar(session.query(Dataset).all()):
        
        if not dataset.slopes:
            slopes = Slopes.from_dataset(dataset)
            session.add(slopes)
            n_telemetry += 1
    session.commit()
    print("Created {0:d} telemetry slopes.".format(n_telemetry))
    
@task
def coefficients(parser, args):
    """Main function for parsing."""
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Coefficients
    from astropy.utils.console import ProgressBar
    
    session = Session()
    
    n_telemetry = 0
    print("Generating coefficients...")
    
    for dataset in ProgressBar(session.query(Dataset).all()):
        
        if not dataset.coefficients:
            coefficients = Coefficients.from_dataset(dataset)
            session.add(coefficients)
            n_telemetry += 1
    session.commit()
    print("Created {0:d} telemetry coefficients.".format(n_telemetry))
    
if __name__ == '__main__':
    main()