# -*- coding: utf-8 -*-

import telemetry.ext.fourieranalysis.models

def connect(url='sqlite:///telemetry2.db'):
    """Connect and return a session."""
    # Connect!
    from sqlalchemy import create_engine
    engine = create_engine(url, echo=False)
    
    # Create the Schema!
    from telemetry.models.base import Base
    Base.metadata.create_all(engine)
    
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    return Session
    