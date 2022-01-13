from loguru import logger
import sys


logger.remove()
logger.add('access.log', format='{time} [{level}] {message}', level="WARNING",
           rotation='00:00', compression='zip', backtrace=True, retention="14 days", enqueue=True)


message_reties = 3
message_sending_interval = 2
alerts_recheck_interval = 10
ignore_managed_objects = ['mastertel-reroute-test']

# database settings

database_host = '127.0.0.1'
database_port = 5432
database_name = 'client_alerts'
database_user = 'postgres'
database_password = 'passw0rd'

