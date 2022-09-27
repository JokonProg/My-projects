import sqlalchemy
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, select
from . import metadata


db_clients = sqlalchemy.Table(
    'clients',
    metadata,
    Column('id', Integer, primary_key=True, index=True, autoincrement=True),
    Column('name', String),
    Column('label', String),
    Column('url', String),
    Column('filter', String),
    Column('arbor_api_key', String),
    Column('type', String),
    Column('chat_id', Float),
    Column('no_alert_bps', Float),
    Column('no_sound_bps', Float),
    Column('no_sound_pps', Float),
    Column('telegram_bot_api_key', String),
)
db_emoji_defaults = sqlalchemy.Table(
    'emoji_default',
    metadata,
    Column('importance_high', String),
    Column('importance_medium', String),
    Column('importance_low', String),
    Column('is_fast_detected', String),
)
db_clients_emoji = sqlalchemy.Table(
    'clients_emoji',
    metadata,
    Column('client_id', ForeignKey('clients.id'), primary_key=True),
    Column('importance_high', String),
    Column('importance_medium', String),
    Column('importance_low', String),
    Column('is_fast_detected', String),
)
db_messages_templates = sqlalchemy.Table(
    'messages_templates',
    metadata,
    Column('client_id', ForeignKey('clients.id'), primary_key=True),
    Column('text', String)
)
db_message_template_default = sqlalchemy.Table(
    'message_template_default',
    metadata,
    Column('text', String)
)
db_active_alerts = sqlalchemy.Table(
    'active_alerts',
    metadata,
    Column('client_id', ForeignKey('clients.id')),
    Column('alert_id', Float),
    Column('message_id', Float),
    Column('managed_object', String),
    Column('alert_type', String),
    Column('bps', String),
    Column('pps', String),
    Column('importance', String),
    Column('is_fast_detected', Boolean),
    Column('duration', String),
    Column('ongoing', Boolean),
    Column('ip', String),
    Column('severity_pct', String),
    Column('misuseTypes', String),
)