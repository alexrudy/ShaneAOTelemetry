#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Initialize a Telemetry database.
"""
from telemetry.application import app
from telemetry.models import Dataset, TelemetryKind
from telemetry.models import (Periodogram, TransferFunction, TelemetryPrerequisite, 
    TransferFunctionFit)
from telemetry.models import (SlopeVectorX, SlopeVectorY, HCoefficients, 
    PseudoPhase, FourierCoefficients, HEigenvalues)

def add_kind(session, name, h5path, type_=TelemetryKind):
    """docstring for add_kind"""
    kind = session.query(type_).filter(type_.h5path == h5path).one_or_none()
    if kind is None:
        kind = type_(name=name, h5path=h5path)
    else:
        kind.name = name
    session.add(kind)
    return kind
    
def add_prerequisite(session, source, prerequisite):
    """Add a prerequisite."""
    if prerequisite not in source.prerequisites:
        tp = TelemetryPrerequisite(source=source, prerequisite=prerequisite)
        session.add(tp)

def main():
    """Main function."""
    app.create_all()
    session = app.session
    
    he = add_kind(session, name="H Eigenvalues", h5path="heigenvalues", type_=HEigenvalues)
    hc = add_kind(session, name="H Coefficients", h5path="hcoefficients", type_=HCoefficients)
    fc = add_kind(session, name="Fourier Coefficients", h5path="fouriercoeffs", type_=FourierCoefficients)
    pp = add_kind(session, name="Pseudo phase", h5path="pseudophase", type_=PseudoPhase)
    sx = add_kind(session, name="X Slopes", h5path="sx", type_=SlopeVectorX)
    sy = add_kind(session, name="Y Slopes", h5path="sy", type_=SlopeVectorY)
    ns = {}
    for key in "slopes tweeter woofer filter tiptilt uplink intermediate".split():
        ns[key] = add_kind(session, name=key, h5path=key)
    slopes = ns['slopes']
    for kind in [he, hc, fc, pp, sx, sy]:
        add_prerequisite(session, kind, slopes)
    for tk in session.query(TelemetryKind).filter(TelemetryKind.h5path.notlike("transferfunction%"), TelemetryKind.h5path.notlike("periodogram%")).all():
        new = Periodogram.from_telemetry_kind(tk.h5path)
        ptk = session.query(TelemetryKind).filter(TelemetryKind.h5path==new.h5path).one_or_none()
        if not ptk:
            ptk = new
        session.add(ptk)
        add_prerequisite(session, ptk, tk)
        
        new = TransferFunction.from_telemetry_kind(tk.h5path)
        ttk = session.query(TelemetryKind).filter(TelemetryKind.h5path==new.h5path).one_or_none()
        if not ttk:
            ttk = new
        session.add(ttk)
        add_prerequisite(session, ttk, ptk)
        
        new = TransferFunctionFit.from_telemetry_kind(tk.h5path)
        tfk = session.query(TelemetryKind).filter(TelemetryKind.h5path==new.h5path).one_or_none()
        if not tfk:
            tfk = new
        tfk._kind = "transferfunctionmodel"
        session.add(tfk)
        add_prerequisite(session, tfk, ttk)
        
        
    for tkm in session.query(TelemetryKind).filter(TelemetryKind.h5path.like("transferfunctionmodel%")).all():
        print(tkm)
        tk = session.query(TelemetryKind).filter(TelemetryKind.h5path==tkm.transferfunction).one()
        add_prerequisite(session, tkm, tk)
    print("\n".join(["{0} {1}".format(repr(tk), tk.prerequisites) for tk in session.query(TelemetryKind).all()]))
    session.commit()


if __name__ == '__main__':
    main()