import datetime
from sqlalchemy import Column, String, Float, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry

from backend.app.db.base import Base

class Responder(Base):
    __tablename__ = "responders"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    
    # Unit type: fire_brigade, hazmat_unit, forest_ranger, medical_team
    type = Column(String, nullable=False, index=True)
    
    # Operational status: AVAILABLE, DISPATCHED, ON_SCENE, OFFLINE
    status = Column(String, nullable=False, default="AVAILABLE", index=True)
    
    # Demo/synthetic contact info (e.g., Radio Ch-4 / Demo Line +91-555-0192)
    contact_info = Column(String, nullable=True)
    organization = Column(String, nullable=True)
    
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Point, SRID 4326, with a spatial index
    geometry = Column(Geometry('POINT', srid=4326, spatial_index=True), nullable=False)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    incidents = relationship("Incident", back_populates="assigned_responder")
    alerts = relationship("Alert", back_populates="recommended_responder")

    __table_args__ = (
        Index("ix_responders_type", "type"),
        Index("ix_responders_status", "status"),
    )
