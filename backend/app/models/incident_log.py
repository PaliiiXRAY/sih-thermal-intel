import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.app.db.base import Base

class IncidentLog(Base):
    __tablename__ = "incident_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(String, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    
    action = Column(String, nullable=False)
    
    # Identifier string (username, user ID, or system component, e.g. "SYSTEM", "ML_PIPELINE", "usr_analyst_1")
    changed_by = Column(String, nullable=True)
    note = Column(String, nullable=True)
    
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True)

    incident = relationship("Incident", back_populates="logs")

    __table_args__ = (
        Index("ix_incident_logs_incident_id", "incident_id"),
        Index("ix_incident_logs_changed_at", "changed_at"),
    )
