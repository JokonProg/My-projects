import sqlalchemy
from sqlalchemy import MetaData, Column, Integer, String, Boolean, Float
from sqlalchemy.orm import declarative_base
import os
import urllib
import databases
from core.settings import database_host, database_port, database_name, database_user, database_password


host_server = os.environ.get('host_server', database_host)
db_server_port = urllib.parse.quote_plus(str(os.environ.get('db_server_port', database_port)))
database_name = os.environ.get('database_name', database_name)
db_username = urllib.parse.quote_plus(str(os.environ.get('db_username', database_user)))
db_password = urllib.parse.quote_plus(str(os.environ.get('db_password', database_password)))
DATABASE_URL = f'postgresql://{db_username}:{db_password}@{host_server}:{db_server_port}/{database_name}'

database = databases.Database(DATABASE_URL)
metadata = MetaData()

alerts_db = sqlalchemy.Table(
    "alerts",
    metadata,
    Column("alert_id", Integer),
    Column("ongoing", Boolean),
    Column("managed_object", String),
    Column("message_id", Float),
    Column("client_type", String),
    Column("client_name", String),
    Column("client_label", String),
    Column("chat_id", Float),
    Column("text", String),
)
