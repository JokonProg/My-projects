import ipaddress
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.exceptions import ValidationError, RequestValidationError
from fastapi.responses import PlainTextResponse
from pydantic import IPvAnyAddress, IPvAnyNetwork, BaseModel
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from typing import List, Union, Optional
import sqlalchemy
from sqlalchemy import Column, String, MetaData, Float, select
import databases
import json

metadata = MetaData()
DATABASE_URL = 'sqlite:///addresses.db'

prefixes = sqlalchemy.Table(
    'prefixes',
    metadata,
    Column('client_id', Float),
    Column('IP_prefix', String)
)

clients = sqlalchemy.Table(
    'clients',
    metadata,
    Column('client_id', Float),
    Column('secret_key', String),
    Column('allowed_prefix', String)
)

database = databases.Database(DATABASE_URL)
engine = sqlalchemy.create_engine(DATABASE_URL)
metadata.create_all(engine)

app = FastAPI(title="DG",
              redoc_url=None,
              swagger_ui_parameters={"defaultModelsExpandDepth": -1, "docExpansion": "list"})

tags_metadata = [
    {
        "name": "Mitigations",
        "description": "Edit mitigation list"
    },
]


class IPPrefixDB(BaseModel):
    client_id: int
    IP_prefix: Union[IPvAnyAddress, IPvAnyNetwork]


class IPPrefix(BaseModel):
    IP_prefix: List[Union[IPv4Address, IPv6Address, IPv4Network, IPv6Network]]

    class Config:
        schema_extra = {
            "example": {
                "IP_prefix": ['127.0.0.1', '10.0.1.0/24', '1050:0:0:0:5:600:300c:326b', '2001:db8::']
            }
        }


async def is_user_exist(client_id: str):
    query = clients.select().where(clients.c.client_id == client_id)
    result = await database.fetch_one(query)
    if result is None or not result:
        raise HTTPException(status_code=403, detail='Client_id invalid')
    else:
        return client_id


async def is_key_valid(secret_key: str, client_id: str):
    query = clients.select().where(clients.c.client_id == client_id)
    result = await database.fetch_one(query)
    if result is None or not result.secret_key == secret_key:
        raise HTTPException(status_code=401, detail='Secret_key invalid')


async def is_allowed_prefix(client_id: int, ip_prefix: Union[IPvAnyAddress, IPvAnyNetwork]) -> bool:
    query = select(clients.c.allowed_prefix).where(clients.c.client_id == client_id)
    result = await database.fetch_one(query)
    result = json.loads(result.allowed_prefix)
    ip_prefix = ipaddress.ip_network(ip_prefix)
    try:
        for prefix in result:
            prefix = ipaddress.ip_network(prefix)
            return all(ip in [ipaddr for ipaddr in prefix.hosts()] for ip in [ipaddr for ipaddr in ip_prefix.hosts()])
    except TypeError:
        return False


async def get_active_prefixes_for_client_from_database(client_id: int) -> list:
    query = select(prefixes.c.IP_prefix).where(prefixes.c.client_id == client_id)
    result = await database.fetch_one(query)
    if result:
        result = json.loads(result.IP_prefix)
        return result
    else:
        return list()


async def get_active_addresses_for_client_from_database(client_id: int) -> Optional[list]:
    query = select(prefixes.c.IP_prefix).where(prefixes.c.client_id == client_id)
    result = await database.fetch_one(query)
    if result:
        addresses = list()
        result = json.loads(result.IP_prefix)
        [[addresses.append(ip) for ip in subnet] for subnet in [ipaddress.ip_network(str_subnet) for str_subnet in result]]
        return addresses
    else:
        return list()


@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc):
    return PlainTextResponse('Bad request', status_code=400)


@app.exception_handler(RequestValidationError)
async def another_validation_error_handler(request, exc):
    return PlainTextResponse('Bad request', status_code=400)


@app.exception_handler(Exception)
async def global_error_handler(request, exc):
    return PlainTextResponse('Bad request', status_code=400)


@app.get("/mitigator/{client_id}/{secret_key}/status", tags=["Mitigations"])
async def get_list_of_banned_addresses(client_id: str = Depends(is_user_exist),
                                       secret_key: str = Depends(is_key_valid)):
    """Get list of active prefixes"""
    result = await get_active_prefixes_for_client_from_database(client_id)
    return {'IP_prefix': result}


@app.post("/mitigator/{client_id}/{secret_key}/start", tags=["Mitigations"])
async def start_filtering_for_prefix(IP_prefix: IPPrefix,
                                     client_id: int = Depends(is_user_exist),
                                     secret_key: str = Depends(is_key_valid)):
    """Start filtering"""
    success = list()
    invalid = list()
    active_addresses = set(await get_active_addresses_for_client_from_database(client_id))
    already_active = list()
    for IP in IP_prefix.IP_prefix:
        if await is_allowed_prefix(client_id=client_id, ip_prefix=IP):
            network = ipaddress.ip_network(IP)
            new_addresses = [ip for ip in network]
            if all(ip in active_addresses for ip in new_addresses):
                already_active.append(IP)
            else:
                active_addresses.update(new_addresses)
                success.append(IP)
        else:
            invalid.append(IP)
    active_subnets = [subnet for subnet in ipaddress.collapse_addresses([ipaddress.ip_network(str(ip)) for ip in list(active_addresses)])]
    if len(await get_active_prefixes_for_client_from_database(client_id)) != 0:
        query = prefixes.update().values(IP_prefix=json.dumps([str(subnet) for subnet in active_subnets])).where(prefixes.c.client_id == client_id)
        await database.execute(query)
    else:
        query = prefixes.insert().values(client_id=client_id, IP_prefix=json.dumps([str(subnet) for subnet in active_subnets]))
        await database.execute(query)
    if len(success) == 0:
        answer = dict()
        if active_subnets:
            answer['IP_prefix is active'] = [str(ip) for ip in active_subnets]
        if invalid:
            answer['IP_prefix invalid'] = [str(ip) for ip in invalid]
        return Response(content=json.dumps(answer), status_code=400, media_type="application/json")
    else:
        answer = dict()
        if success:
            answer['success'] = success
        if already_active:
            answer['IP_prefix is active'] = already_active
        if invalid:
            answer['IP_prefix invalid'] = invalid
        return answer


@app.post("/mitigator/{client_id}/{secret_key}/stop", tags=["Mitigations"])
async def stop_filtering_for_prefix(IP_prefix: IPPrefix,
                                    client_id: int = Depends(is_user_exist),
                                    secret_key: str = Depends(is_key_valid)):
    """Stop filtering"""
    success = list()
    inactive = list()
    invalid = list()
    print(IP_prefix)
    active_addresses = set(await get_active_addresses_for_client_from_database(client_id))
    for IP in IP_prefix.IP_prefix:
        if await is_allowed_prefix(client_id=client_id, ip_prefix=IP):
            network = ipaddress.ip_network(IP)
            delete_addresses = [ip for ip in network]
            if any(ip in active_addresses for ip in delete_addresses):
                for ip in delete_addresses:
                    try:
                        active_addresses.remove(ip)
                    except ValueError:
                        pass
                    except KeyError:
                        pass
                success.append(IP)
            else:
                inactive.append(IP)
                """Nothing to delete"""
            active_subnets = [subnet for subnet in ipaddress.collapse_addresses(
                [ipaddress.ip_network(str(ip)) for ip in list(active_addresses)])]
            if len(await get_active_prefixes_for_client_from_database(client_id)) != 0:
                if len(active_subnets) == 0:
                    query = prefixes.delete().where(prefixes.c.client_id == client_id)
                    await database.execute(query)
                else:
                    query = prefixes.update().values(IP_prefix=json.dumps([str(subnet) for subnet in active_subnets])).where(prefixes.c.client_id == client_id)
                    await database.execute(query)
            else:
                query = prefixes.insert().values(client_id=client_id,
                                                 IP_prefix=json.dumps([str(subnet) for subnet in active_subnets]))
                await database.execute(query)
        else:
            invalid.append(IP)
    answer = dict()
    if len(success) == 0:
        if inactive:
            answer['IP_prefix is not active'] = [str(ip) for ip in inactive]
        if invalid:
            answer['IP_prefix invalid'] = [str(ip) for ip in invalid]
        return Response(content=json.dumps(answer), status_code=400, media_type="application/json")
    else:
        answer['success'] = success
        if inactive:
            answer['IP_prefix is not active'] = [str(ip) for ip in inactive]
        if invalid:
            answer['IP_prefix invalid'] = [str(ip) for ip in invalid]
        return answer
