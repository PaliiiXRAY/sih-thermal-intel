import datetime
from sqlalchemy import Column, String, Float, DateTime, Index
from sqlalchemy.sql import func
from geoalchemy2 import Geometry

from backend.app.db.base import Base

class Hotspot(Base):
    __tablename__ = "hotspots"

    id = Column(String, primary_key=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Point, SRID 4326, with a spatial index
    geometry = Column(Geometry('POINT', srid=4326, spatial_index=True), nullable=False)
    
    acquisition_time = Column(DateTime(timezone=True), nullable=False)
    satellite = Column(String, nullable=True)
    instrument = Column(String, nullable=True)
    
    frp = Column(Float, nullable=True)
    bright_ti4 = Column(Float, nullable=True)
    bright_ti5 = Column(Float, nullable=True)
    
    # NASA/FIRMS detection confidence, distinct from ML classification confidence
    detection_confidence = Column(String, nullable=True)
    
    source = Column(String, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_hotspots_acquisition_time", "acquisition_time"),
        Index("ix_hotspots_source", "source"),
    )
