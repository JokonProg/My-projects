import sqlalchemy
from sqlalchemy import MetaData
import databases

metadata = MetaData()
host_server = 'server'
db_server_port = 5432
database_name = 'arborbot'
db_username = 'pg_user'
db_password = ''
DATABASE_URL = f'postgresql://{db_username}:{db_password}@{host_server}:{db_server_port}/{database_name}'


database = databases.Database(DATABASE_URL)
engine = sqlalchemy.create_engine(DATABASE_URL, pool_size=3, max_overflow=0, echo=False)
