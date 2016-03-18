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
    
DATA_KINDS = set("sx sy hcoefficients fmodes phase pseudophase".split())
    
def main():
    """Set up the argument parser."""
    
    from telemetry.models import HCoefficients, Phase, FourierCoefficients, PseudoPhase, Slopes, Tweeter
    create(HCoefficients)
    create(Phase)
    create(FourierCoefficients)
    create(Slopes)
    create(PseudoPhase)
    create(Tweeter)
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("task", choices=__tasks.keys())
    opt, args = parser.parse_known_args()
    
    subparser = argparse.ArgumentParser(sys.argv[0] + " {0}".format(opt.task))
    
    __tasks[opt.task](subparser, args)
    
def create(model):
    """Create a specific model object."""
    
    def task(parser, args):
        """Main function for parsing."""
        parser.add_argument("-f", "--force", action='store_true', help="Force")
        opt = parser.parse_args(args)
        from telemetry import connect
        Session = connect()
        from telemetry.models import Dataset
        from astropy.utils.console import ProgressBar
    
        session = Session()
    
        n_telemetry = 0
        print("Generating {0}...".format(model.__name__))
    
        for dataset in ProgressBar(session.query(Dataset).all()):
            if opt.force or not session.query(model).filter(model.dataset_id == dataset.id).count() >= 1:
                try:
                    obj = model.from_dataset(dataset)
                    session.add(obj)
                except ValueError as e:
                    pass
                else:
                    n_telemetry += 1
        session.commit()
        print("Created {0:d} telemetry {1:s}.".format(n_telemetry, model.__name__))
    
    __tasks[model.__name__.lower()] = task
    
@task
def periodograms(parser, args):
    """Main function for parsing."""
    parser.add_argument("-f", "--force", action='store_true', help="Force creation of periodograms")
    parser.add_argument("-l", "--length", type=int, help="Periodogram length", default=1024)
    parser.add_argument("-s", "--suppress-static", action='store_true', help="Suppress static in PSDs")
    opt = parser.parse_args(args)
    
    from telemetry import connect
    Session = connect()
    from telemetry.models import Dataset, Periodogram, PeriodogramStack, Sequence
    session = Session()
    from astropy.utils.console import ProgressBar
    
    n_telemetry = 0
    
    print("Generating periodograms...")
    for sequence in ProgressBar(session.query(Sequence).all()):
        for kind in DATA_KINDS:
            if opt.force or kind not in sequence.periodograms:
                try:
                    pgram = PeriodogramStack.from_sequence(sequence, kind, opt.length, suppress_static=opt.suppress_static)
                    session.add(pgram)
                except Exception as e:
                    print(repr(e))
                else:
                    n_telemetry += 1
    session.commit()
    print("Created {0:d} periodograms.".format(n_telemetry))
    
@task
def tf(parser, args):
    """Create transfer functions."""
    parser.add_argument("-f", "--force", action='store_true', help="Force")
    
    opt = parser.parse_args(args)
    
    from telemetry.models import Dataset, PeriodogramStack, Sequence, TransferFunction
    from telemetry import connect
    Session = connect()
    session = Session()
    from astropy.utils.console import ProgressBar
    
    for sequence in ProgressBar(session.query(Sequence).filter(Sequence.pair_id != None, Sequence.loop == "closed").all()):
        for kind in DATA_KINDS:
            tf = TransferFunction.from_periodogram(sequence.periodograms[kind])
            session.add(tf)
    print("Created {0:d} transfer functions.".format(len(session.new) + len(session.dirty)))
    session.commit()
    
@task
def tffit(parser, args):
    """Make a transfer function fits."""
    opt = parser.parse_args(args)
    
    from telemetry import connect
    from telemetry.models import TransferFunction, TransferFunctionModel
    Session = connect()
    from telemetry.algorithms.transfer.linfit import expected_model, fit_model, fit_all_models
    
    session = Session()
    from astropy.utils.console import ProgressBar
    
    for tf in ProgressBar(session.query(TransferFunction).all()):
        if tf.kind in tf.sequence.transferfunctionmodels:
            continue
        model = fit_all_models(tf)
        tfm = TransferFunctionModel.from_model(tf, model)
        session.add(tfm)
    session.commit()
    
if __name__ == '__main__':
    main()