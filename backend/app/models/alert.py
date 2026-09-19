import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Index, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.app.db.base import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(String, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    
    alert_type = Column(String, nullable=False)
    target_role = Column(String, nullable=True)
    recommended_responder_id = Column(String, ForeignKey("responders.id", ondelete="SET NULL"), nullable=True, index=True)
    
    is_simulated = Column(Boolean, nullable=False, default=True)
    status = Column(String, nullable=False, default="PENDING")
    message = Column(String, nullable=True)
    
    payload = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    
    metadata_ = Column("metadata", JSONB, nullable=True)

    incident = relationship("Incident", back_populates="alerts")
    recommended_responder = relationship("Responder", back_populates="alerts")

    __table_args__ = (
        Index("ix_alerts_incident_id", "incident_id"),
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_created_at", "created_at"),
        Index("ix_alerts_recommended_responder_id", "recommended_responder_id"),
    )
