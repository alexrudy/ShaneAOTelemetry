#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Initialize a Telemetry database.
"""

def main():
    """Main function."""
    from telemetry import connect
    from telemetry.models import Dataset, TelemetryKind, Periodogram, TransferFunction
    from telemetry.models import (SlopeVectorX, SlopeVectorY, HCoefficients, 
        PseudoPhase, FourierCoefficients, HEigenvalues)
    session = connect()()
    try:
        he = HEigenvalues(name="H Eigenvalues", h5path="heigenvalues")
        session.add(he)
    
        hc = HCoefficients(name="H Coefficients", h5path="hcoefficients")
        session.add(hc)
    
        fc = FourierCoefficients(name="Fourier Coefficients", h5path="fouriercoeffs")
        session.add(fc)
    
        pp = PseudoPhase(name="Pseudo phase", h5path="pseudophase")
        session.add(pp)
    
        sx = SlopeVectorX(name="X Slopes", h5path="sx")
        session.add(sx)
        sy = SlopeVectorY(name="Y Slopes", h5path="sy")
        session.add(sy)
    
        tks = [TelemetryKind(name=key, h5path=key) for key in "slopes tweeter woofer filter tiptilt uplink intermediate".split()]
        session.add_all(tks)
        session.commit()
    except Exception:
        print("Rollback")
        session.rollback()
    try:
        tk = TelemetryKind(name="intermediate", h5path="intermediate")
        session.add(tk)
        session.commit()
    except Exception:
        print("Rollback")
        session.rollback()
    try:
        for tk in session.query(TelemetryKind).all():
            ptk = Periodogram.from_telemetry_kind(tk.h5path)
            ttk = TransferFunction.from_telemetry_kind(tk.h5path)
            session.add(ptk)
            session.add(ttk)
        session.commit()
    except Exception:
        print("Rollback")
        session.rollback()
    print("\n".join([repr(tk) for tk in session.query(TelemetryKind).all()]))
    

if __name__ == '__main__':
    main()