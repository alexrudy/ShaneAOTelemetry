# -*- coding: utf-8 -*-

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

def connect(url='sqlite:///telemetry2.db'):
    """Connect and return a session."""
    # Connect!
    engine = create_engine(url, echo=False)
    
    # Create the Schema!
    from telemetry.models.base import Base
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    return Session
    

