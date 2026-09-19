"""Initial migration

Revision ID: f0ee81829371
Revises: 
Create Date: 2026-09-18 23:09:50.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = 'f0ee81829371'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable PostGIS
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis;')

    # 2. Create Hotspots Table
    op.create_table(
        'hotspots',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('geometry', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=False),
        sa.Column('acquisition_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('satellite', sa.String(), nullable=True),
        sa.Column('instrument', sa.String(), nullable=True),
        sa.Column('frp', sa.Float(), nullable=True),
        sa.Column('bright_ti4', sa.Float(), nullable=True),
        sa.Column('bright_ti5', sa.Float(), nullable=True),
        sa.Column('detection_confidence', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hotspots_id'), 'hotspots', ['id'], unique=False)
    op.create_index('ix_hotspots_acquisition_time', 'hotspots', ['acquisition_time'], unique=False)
    op.create_index('ix_hotspots_source', 'hotspots', ['source'], unique=False)

    # 3. Create Incidents Table
    op.create_table(
        'incidents',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='NEW'),
        sa.Column('classification', sa.String(), nullable=True),
        sa.Column('classification_confidence', sa.Float(), nullable=True),
        sa.Column('detection_confidence', sa.String(), nullable=True),
        sa.Column('persistence_score', sa.Float(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('severity', sa.String(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('geometry', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=False),
        sa.Column('explanation', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_incidents_id'), 'incidents', ['id'], unique=False)
    op.create_index('ix_incidents_status', 'incidents', ['status'], unique=False)
    op.create_index('ix_incidents_severity', 'incidents', ['severity'], unique=False)
    op.create_index('ix_incidents_classification', 'incidents', ['classification'], unique=False)

    # 4. Create IncidentLogs Table
    op.create_table(
        'incident_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('incident_id', sa.String(), nullable=False),
        sa.Column('old_status', sa.String(), nullable=True),
        sa.Column('new_status', sa.String(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('actor', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_incident_logs_id'), 'incident_logs', ['id'], unique=False)
    op.create_index('ix_incident_logs_incident_id', 'incident_logs', ['incident_id'], unique=False)
    op.create_index('ix_incident_logs_timestamp', 'incident_logs', ['timestamp'], unique=False)

    # 5. Create Alerts Table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('incident_id', sa.String(), nullable=False),
        sa.Column('alert_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='PENDING'),
        sa.Column('message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alerts_id'), 'alerts', ['id'], unique=False)
    op.create_index('ix_alerts_incident_id', 'alerts', ['incident_id'], unique=False)
    op.create_index('ix_alerts_status', 'alerts', ['status'], unique=False)
    op.create_index('ix_alerts_created_at', 'alerts', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('alerts')
    op.drop_table('incident_logs')
    op.drop_table('incidents')
    op.drop_table('hotspots')
    op.execute('DROP EXTENSION IF EXISTS postgis;')
