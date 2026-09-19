import datetime
from sqlalchemy import Column, String, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from geoalchemy2 import Geometry

from backend.app.db.base import Base

class Asset(Base):
    __tablename__ = "assets"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    
    # Kind: facility, settlement, road, shelter, pipeline, industrial_plant, protected_area
    type = Column(String, nullable=False, index=True)
    
    # Broader context/risk category: critical_infrastructure, human_settlement, eco_reserve
    category = Column(String, nullable=True)
    
    risk_weight = Column(Float, nullable=True, default=1.0)
    
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Point, SRID 4326, with a spatial index
    geometry = Column(Geometry('POINT', srid=4326, spatial_index=True), nullable=False)
    
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_assets_type", "type"),
    )
