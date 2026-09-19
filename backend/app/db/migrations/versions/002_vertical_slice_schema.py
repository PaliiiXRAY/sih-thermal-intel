"""Vertical Slice Schema Migration (Users, Assets, Responders, Alerts, IncidentLogs, Incidents)

Revision ID: a2b3c4d5e6f7
Revises: f0ee81829371
Create Date: 2026-09-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'f0ee81829371'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('role', sa.String(), server_default='analyst', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)

    # 2. Create Assets Table
    op.create_table(
        'assets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('risk_weight', sa.Float(), server_default='1.0', nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('geometry', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assets_id'), 'assets', ['id'], unique=False)
    op.create_index(op.f('ix_assets_type'), 'assets', ['type'], unique=False)

    # 3. Create Responders Table
    op.create_table(
        'responders',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), server_default='AVAILABLE', nullable=False),
        sa.Column('contact_info', sa.String(), nullable=True),
        sa.Column('organization', sa.String(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('geometry', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_responders_id'), 'responders', ['id'], unique=False)
    op.create_index(op.f('ix_responders_type'), 'responders', ['type'], unique=False)
    op.create_index(op.f('ix_responders_status'), 'responders', ['status'], unique=False)

    # 4. Alter Incidents Table
    op.add_column('incidents', sa.Column('assigned_responder_id', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_incidents_assigned_responder_id',
        'incidents', 'responders',
        ['assigned_responder_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index(op.f('ix_incidents_assigned_responder_id'), 'incidents', ['assigned_responder_id'], unique=False)
    op.alter_column('incidents', 'status', server_default='DETECTED')
    # Update any existing legacy rows cleanly
    op.execute("UPDATE incidents SET status = 'DETECTED' WHERE status = 'NEW';")

    # 5. Alter Alerts Table
    op.add_column('alerts', sa.Column('target_role', sa.String(), nullable=True))
    op.add_column('alerts', sa.Column('recommended_responder_id', sa.String(), nullable=True))
    op.add_column('alerts', sa.Column('is_simulated', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('alerts', sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_foreign_key(
        'fk_alerts_recommended_responder_id',
        'alerts', 'responders',
        ['recommended_responder_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index(op.f('ix_alerts_recommended_responder_id'), 'alerts', ['recommended_responder_id'], unique=False)

    # 6. Alter IncidentLogs Table
    op.alter_column('incident_logs', 'actor', new_column_name='changed_by')
    op.alter_column('incident_logs', 'timestamp', new_column_name='changed_at')
    op.add_column('incident_logs', sa.Column('note', sa.String(), nullable=True))
    op.drop_index('ix_incident_logs_timestamp', table_name='incident_logs')
    op.create_index(op.f('ix_incident_logs_changed_at'), 'incident_logs', ['changed_at'], unique=False)


def downgrade() -> None:
    # 6. Revert IncidentLogs Table
    op.drop_index(op.f('ix_incident_logs_changed_at'), table_name='incident_logs')
    op.create_index('ix_incident_logs_timestamp', 'incident_logs', ['changed_at'], unique=False)
    op.drop_column('incident_logs', 'note')
    op.alter_column('incident_logs', 'changed_at', new_column_name='timestamp')
    op.alter_column('incident_logs', 'changed_by', new_column_name='actor')

    # 5. Revert Alerts Table
    op.drop_constraint('fk_alerts_recommended_responder_id', 'alerts', type_='foreignkey')
    op.drop_index(op.f('ix_alerts_recommended_responder_id'), table_name='alerts')
    op.drop_column('alerts', 'payload')
    op.drop_column('alerts', 'is_simulated')
    op.drop_column('alerts', 'recommended_responder_id')
    op.drop_column('alerts', 'target_role')

    # 4. Revert Incidents Table
    op.alter_column('incidents', 'status', server_default='NEW')
    op.drop_constraint('fk_incidents_assigned_responder_id', 'incidents', type_='foreignkey')
    op.drop_index(op.f('ix_incidents_assigned_responder_id'), table_name='incidents')
    op.drop_column('incidents', 'assigned_responder_id')

    # 3. Drop Responders Table
    op.drop_table('responders')

    # 2. Drop Assets Table
    op.drop_table('assets')

    # 1. Drop Users Table
    op.drop_table('users')
