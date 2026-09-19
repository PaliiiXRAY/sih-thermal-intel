import datetime
from sqlalchemy import Column, String, Float, DateTime, Integer, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry

from backend.app.db.base import Base

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, index=True)
    
    # Canonical states: DETECTED -> CLASSIFIED -> ASSESSED -> ALERTED -> ACKNOWLEDGED -> RESOLVED (sub-statuses: EN_ROUTE, ARRIVED, CONTAINED)
    status = Column(String, nullable=False, default="DETECTED")
    
    # Canonical classifications: INDUSTRIAL_FIRE, GAS_FLARE, WILDFIRE, CROP_BURNING, MINING_OTHER, UNKNOWN
    classification = Column(String, nullable=True)
    classification_confidence = Column(Float, nullable=True)
    detection_confidence = Column(String, nullable=True)
    persistence_score = Column(Float, nullable=True)
    
    # Priority risk score (0-100), NOT a probability
    risk_score = Column(Float, nullable=True)
    severity = Column(String, nullable=True)
    
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Point, SRID 4326, with a spatial index
    geometry = Column(Geometry('POINT', srid=4326, spatial_index=True), nullable=False)
    
    explanation = Column(JSONB, nullable=True)
    
    assigned_responder_id = Column(String, ForeignKey("responders.id", ondelete="SET NULL"), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    logs = relationship("IncidentLog", back_populates="incident", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="incident", cascade="all, delete-orphan")
    assigned_responder = relationship("Responder", back_populates="incidents")

    __table_args__ = (
        Index("ix_incidents_status", "status"),
        Index("ix_incidents_severity", "severity"),
        Index("ix_incidents_classification", "classification"),
        Index("ix_incidents_assigned_responder_id", "assigned_responder_id"),
    )
