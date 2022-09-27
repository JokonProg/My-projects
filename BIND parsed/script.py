import datetime
import json
import xml.etree.ElementTree as ET
from pydantic import BaseModel, Field
from typing import Optional
import sqlalchemy
from sqlalchemy import create_engine, MetaData, Column, Integer, String, DateTime, Date
from sqlalchemy.orm import Session
from enum import Enum
import sys
from loguru import logger


logger.remove()
logger.add('access.log', format='{time} [{level}] {message}', level='DEBUG',
           rotation='00:00', compression='zip', backtrace=True)


host_server = 'IP_address'
db_server_port = 5432
database_name = 'dns'
db_username = 'pg_user'
db_password = 'password'
DATABASE_URL = f'postgresql://{db_username}:{db_password}@{host_server}:{db_server_port}/{database_name}'
metadata = MetaData()
PATH_TO_XML = sys.argv[1]

db_zones = sqlalchemy.Table(
    'zones',
    metadata,
    Column('datetime', DateTime, default=datetime.datetime.now()),
    Column('date', Date, default=datetime.date.today()),
    Column('name', String),
    Column('type', String),
    Column('auth_qry_rej', Integer),
    Column('rec_qry_rej', Integer),
    Column('qry_success', Integer),
    Column('qry_auth_ans', Integer),
    Column('qry_noauth_ans', Integer),
    Column('qry_referral', Integer),
    Column('qry_nxrrset', Integer),
    Column('qry_nxdomain', Integer),
    Column('qry_udp', Integer),
    Column('qry_tcp', Integer),
)

engine = create_engine(
    DATABASE_URL, pool_size=3, max_overflow=0, echo=False
)
#metadata.drop_all(engine) #use if you need to drop table
metadata.create_all(engine)

start = datetime.datetime.now()


class ZoneMode(Enum):
    update = 'update'
    current = 'current'
    zero = 'zero'


class Zone(BaseModel):
    name: str
    type: str
    AuthQryRej: Optional[int] = Field(0, alias='auth_qry_rej')
    RecQryRej: Optional[int] = Field(0, alias='rec_qry_rej')
    QrySuccess: Optional[int] = Field(0, alias='qry_success')
    QryAuthAns: Optional[int] = Field(0, alias='qry_auth_ans')
    QryNoauthAns: Optional[int] = Field(0, alias='qry_noauth_ans')
    QryReferral: Optional[int] = Field(0, alias='qry_referral')
    QryNxrrset: Optional[int] = Field(0, alias='qry_nxrrset')
    QryNXDOMAIN: Optional[int] = Field(0, alias='qry_nxdomain')
    QryUDP: Optional[int] = Field(0, alias='qry_udp')
    QryTCP: Optional[int] = Field(0, alias='qry_tcp')

    class Config:
        allow_population_by_field_name = True


@logger.catch()
def compare(current: Zone, previous: Zone) -> ZoneMode:
    logger.debug(f'Get {current=} and {previous=}')
    if (current.AuthQryRej >= previous.AuthQryRej and current.RecQryRej >= previous.RecQryRej and
            current.QrySuccess >= previous.QrySuccess and current.QryAuthAns >= previous.QryAuthAns and
            current.QryNoauthAns >= previous.QryNoauthAns and current.QryReferral >= previous.QryReferral and
            current.QryNxrrset >= previous.QryNxrrset and current.QryNXDOMAIN >= previous.QryNXDOMAIN and
            current.QryUDP >= previous.QryUDP and current.QryTCP >= previous.QryTCP):
        # The counters are increased, it is necessary to consider the difference
        logger.debug('result is "UPDATE"')
        return ZoneMode.update
    elif (current.AuthQryRej == previous.AuthQryRej and current.RecQryRej == previous.RecQryRej and
            current.QrySuccess == previous.QrySuccess and current.QryAuthAns == previous.QryAuthAns and
            current.QryNoauthAns == previous.QryNoauthAns and current.QryReferral == previous.QryReferral and
            current.QryNxrrset == previous.QryNxrrset and current.QryNXDOMAIN == previous.QryNXDOMAIN and
            current.QryUDP == previous.QryUDP and current.QryTCP == previous.QryTCP):
        # Counters not incremented
        logger.debug('result is "ZERO"')
        return ZoneMode.zero
    elif (current.AuthQryRej < previous.AuthQryRej or current.RecQryRej < previous.RecQryRej or
            current.QrySuccess < previous.QrySuccess or current.QryAuthAns < previous.QryAuthAns or
            current.QryNoauthAns < previous.QryNoauthAns or current.QryReferral < previous.QryReferral or
            current.QryNxrrset < previous.QryNxrrset or current.QryNXDOMAIN < previous.QryNXDOMAIN or
            current.QryUDP < previous.QryUDP or current.QryTCP < previous.QryTCP):
        # Some of the counters have decreased, the server has rebooted, the current state is the difference in values
        logger.debug('result is "CURRENT"')
        return ZoneMode.current


@logger.catch()
def calculate_lambda(cur_zone: Zone, prev_zone: Zone) -> Zone:
    result = dict()
    result['name'] = cur_zone.name
    result['type'] = cur_zone.type
    for key in cur_zone.dict():
        if key not in ['name', 'type'] and cur_zone.dict()[key]:
            result[key] = cur_zone.dict()[key] - prev_zone.dict()[key]
        else:
            result[key] = cur_zone.dict()[key]
    result = Zone.parse_obj(result)
    logger.debug(f'Lambda is {result}')
    return result


@logger.catch()
def parse():
    logger.debug('Started parser')
    tree = ET.parse(PATH_TO_XML)
    root = tree.getroot()
    views = root.findall("./views/view")
    zones = views[0][0]
    all_zones = list()
    for zone in zones:
        zone_elem = dict()
        zone_elem['name'] = zone.get('name')
        zone_elem['type'] = zone.find('type').text
        if zone_elem['type'] != 'builtin':
            counters = zone.findall('counters')
            for counter in counters:
                elements = counter.findall('counter')
                for element in elements:
                    zone_elem[element.get('name')] = int(element.text)
            zone_elem = Zone.parse_obj(zone_elem)
            all_zones.append(zone_elem.dict())
    logger.debug(f'Parsed elements {all_zones}')
    return all_zones


@logger.catch()
def main():
    zones = parse()
    lambda_zones = list()
    try:
        with open('last_state.json', mode='r+') as file:
            lasts = json.loads(file.read())
            for cur_zone in zones:
                lambda_zone = dict()
                cur_zone = Zone.parse_obj(cur_zone)
                try:
                    previous_zone = [x for x in lasts if x.get('name') == cur_zone.name][0]
                    previous_zone = Zone.parse_obj(previous_zone)
                    logger.debug(f'Previous zone get {previous_zone}')
                    result = compare(current=cur_zone, previous=previous_zone)
                    match result:
                        case ZoneMode.zero:
                            logger.debug('Nothing to add')
                            pass
                        case ZoneMode.update:
                            lambda_zone = calculate_lambda(cur_zone, previous_zone)
                            lambda_zones.append(lambda_zone.dict(by_alias=True))
                            logger.debug(f'Added in lambda_zones list {lambda_zone.dict(by_alias=True)}')
                        case ZoneMode.current:
                            lambda_zone = cur_zone
                            lambda_zones.append(lambda_zone.dict(by_alias=True))
                            logger.debug(f'Added in lambda_zones list {lambda_zone.dict(by_alias=True)}')
                except IndexError:
                    lambda_zone = cur_zone
        with Session(engine) as session:
            query = db_zones.insert().values(lambda_zones)
            session.execute(query)
            session.commit()
            logger.debug('Result in database')
        with open('last_state.json', mode='w') as file:
            file.write(json.dumps(zones))
    except FileNotFoundError:
        with open('last_state.json', mode='w') as file:
            file.write(json.dumps(zones))


if __name__ == '__main__':
    logger.debug('Program Started')
    main()
    logger.debug('Program closed')

