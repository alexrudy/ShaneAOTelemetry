# -*- coding: utf-8 -*-

def connect(url='sqlite:///telemetry.db'):
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
    
def makedirs(dirname):
    """Make directories."""
    import os
    try:
        os.makedirs(dirname)
    except OSError as e:
        if not os.path.exists(dirname):
            raise
        