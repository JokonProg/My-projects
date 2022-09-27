import time, os, sys
from datetime import datetime, timedelta, timezone
import asyncio
import aiohttp
import loguru
from loguru import logger
from pydantic import BaseModel, Field
from typing import Optional, List
import json
from arbor import ArborAlert
from telegram_queue_models import TelegramQueueElement
from database import database, engine, metadata
from database.models import db_clients, db_clients_emoji, db_emoji_defaults, db_active_alerts, \
    db_message_template_default, db_messages_templates, select


log_dir = 'logs/'
log_file = 'access.log'
log_level = 'debug'
log_retention = '2 days'

# metadata.drop_all(engine) #uncomment if you want to clear database
metadata.create_all(engine)
logfile = log_dir + log_file
logger.remove()
logger.add(logfile, format='{time} [{level}] {message}', level=log_level.upper(),
           rotation='00:00', compression='zip', backtrace=True, retention=log_retention)


class ClientElement(BaseModel):
    id: Optional[int]
    name: str
    label: str
    url: str
    filter: str
    arbor_api_key: str
    type: Optional[str] = 'Telegram'
    chat_id: int
    no_alert_bps: Optional[int] = 0
    no_sound_bps: Optional[int] = 0
    no_sound_pps: Optional[int] = 0
    telegram_bot_api_key: str


class AlertMessageArguments(BaseModel):
    chat_id: int
    message_id: int = 0
    label: str
    alert_type: str
    id: int = Field(None, alias='alert_id')
    managed_object: str
    bps: str
    pps: str
    importance: str
    is_fast_detected: bool = False
    duration: str
    ongoing: bool
    ip: Optional[str]
    severity_pct: str
    misuseTypes: Optional[str]


class ClientEmoji(BaseModel):
    high: str = Field(None, alias='importance_high')
    medium: str = Field(None, alias='importance_medium')
    low: str = Field(None, alias='importance_low')
    is_fast_detected: str


# begin formatting functions
def bps_formatted(bps: int) -> str:
    if round(bps / 1000000, 2) < 1000:
        bps = round(int(bps) / 1000000, 2)
        bps = str(bps) + ' Mbps'
    else:
        bps = round(int(bps) / 1000000000, 2)
        bps = str(bps) + ' Gbps'
    return bps


def pps_formatted(pps: int) -> str:
    if round(int(pps) / 1000, 2) < 1000:
        pps = round(int(pps) / 1000, 2)
        pps = str(pps) + ' Kpps'
    else:
        pps = round(int(pps) / 1000000, 2)
        pps = str(pps) + ' Mpps'
    return pps


def misuse_types_formatted(misuse_types) -> Optional[str]:
    try:
        return ', '.join(misuse_types)
    except TypeError:
        return None


# end formatting functions

# begin database functions

@logger.catch
async def get_clients() -> List[ClientElement]:
    logger.debug('Inside get clients')
    query = db_clients.select()
    clients = await database.fetch_all(query)
    result = list()
    for client in clients:
        result.append(ClientElement.parse_obj(client))
    return result


@logger.catch()
async def write_client():
    with open('clients.json', mode='r') as file:
        text = file.read()
        clients = json.loads(text)
        clients_to_db = list()
        for client in clients:
            clients_to_db.append(ClientElement.parse_obj(client))
        query = db_clients.insert().values(clients)
        last_record_id = await database.execute(query)
        logger.debug(last_record_id)


@logger.catch()
async def drop_client_alerts_ongoing(client_id: int) -> None:
    query = db_active_alerts.update().values(ongoing=False).where(db_active_alerts.c.client_id == client_id)
    logger.debug(f'For client_id={client_id} prepared query: {query}')
    await database.execute(query)
    logger.debug(f'Ongoing dropped for client {client_id}')


@logger.catch()
async def keep_client_alerts_ongoing(client_id: int) -> None:
    query = db_active_alerts.update().values(ongoing=True).where(db_active_alerts.c.client_id == client_id)
    logger.debug(f'For client_id={client_id} prepared query: {query}')
    await database.execute(query)
    logger.debug(f'Returned ongoing for client {client_id}')


@logger.catch
async def save_alert_in_database(client: ClientElement, alert: AlertMessageArguments) -> None:
    query = db_active_alerts.insert().values(client_id=client.id, message_id=alert.message_id, alert_id=alert.id, alert_type=alert.alert_type,
                                             managed_object=alert.managed_object, bps=alert.bps, pps=alert.pps,
                                             importance=alert.importance, is_fast_detected=alert.is_fast_detected,
                                             duration=alert.duration, ongoing=alert.ongoing, ip=alert.ip,
                                             severity_pct=alert.severity_pct, misuseTypes=alert.misuseTypes
                                             )
    await database.execute(query)
    logger.debug(f'For client {client.id} saved alert in db {alert.dict()}')


@logger.catch()
async def get_existing_alert_from_db(client_id: int, alert_id: int) -> Optional[AlertMessageArguments]:
    query = db_active_alerts.join(db_clients).select().where(db_active_alerts.c.client_id == client_id,
                                                             db_active_alerts.c.alert_id == alert_id)
    logger.debug(f'For client_id={client_id} prepared query: {query}')
    result = await database.fetch_one(query)
    if result:
        result = AlertMessageArguments.parse_obj(result)
        logger.debug(f'get_existing_alert_from_db. {result=}')
        return result
    else:
        return None


@logger.catch()
async def update_alert_in_in_db(client_id: int, alert: AlertMessageArguments) -> bool:
    query = db_active_alerts.update().values(alert.dict(exclude={'id', 'chat_id', 'label'})).where(
        db_active_alerts.c.client_id == client_id, db_active_alerts.c.alert_id == alert.id)
    logger.debug(f'For client_id={client_id} prepared query: {query}')
    logger.debug(alert)
    await database.execute(query)
    logger.debug(f'update_alert_in_in_db. For client_id {client_id}: {alert}')
    return True


@logger.catch()
async def update_alert_ongoing_in_db(client_id: int, alert: AlertMessageArguments) -> bool:
    query = db_active_alerts.update().values(ongoing=True).where(
        db_active_alerts.c.client_id == client_id, db_active_alerts.c.alert_id == alert.id)
    logger.debug(f'For client_id={client_id} prepared query: {query}')
    logger.debug(alert)
    await database.execute(query)
    logger.debug(f'For client_id={client_id} updated ongoing for alert {alert}')
    return True


@logger.catch()
async def get_client_message_template(client_id: int) -> str:
    query = select(db_messages_templates.c.text).where(
        db_messages_templates.c.client_id == client_id)  # db_messages_templates.select().where(db_messages_templates.c.client_id == client_id)
    logger.debug(f'For client_id={client_id} prepared query: {query}')
    result = await database.fetch_one(query)
    if not result:
        logger.debug(f'For client {client_id} used default notification template')
        query = select(db_message_template_default.c.text)
        result = await database.fetch_one(query)
    return result.get('text')


@logger.catch()
async def get_client_emoji(client_id: int) -> ClientEmoji:
    query = db_clients_emoji.select().where(
        db_clients_emoji.c.client_id == client_id)
    result = await database.fetch_one(query)
    if not result:
        logger.debug(f'For client {client_id} used default emoji')
        query = db_emoji_defaults.select()
        result = await database.fetch_one(query)
    else:
        logger.debug(f'For client {client_id} used custom emoji')
    result = ClientEmoji.parse_obj(result)
    logger.debug(f'For client {client_id} got emoji {result}')
    return result


@logger.catch()
async def get_solved_alerts(client_id: int) -> Optional[List[AlertMessageArguments]]:
    query = db_active_alerts.join(db_clients).select().where(db_active_alerts.c.client_id == client_id,
                                                             db_active_alerts.c.ongoing == False)
    logger.debug(f'For client_id={client_id} prepared query: {query}')
    alerts = await database.fetch_all(query)
    if len(alerts) > 0:
        result = list()
        for alert in alerts:
            result.append(AlertMessageArguments.parse_obj(alert))
        logger.debug(f'For client_id {client_id} get solved alerts {result}')
        return result
    else:
        logger.debug(f'For client_id {client_id} solved alerts is none')
        return None


@logger.catch()
async def delete_solved_alert_from_database(client_id: int, alert_id: int):
    query = db_active_alerts.delete().where(db_active_alerts.c.client_id == client_id,
                                            db_active_alerts.c.alert_id == alert_id)
    await database.execute(query)
    logger.debug(f'For client id={client_id} deleted alert {alert_id} as solved')


@logger.catch()
async def drop_solved_alerts(client: ClientElement):
    logger.debug(f'For client_id={client.id} start deleting solved alerts.')
    solved_alerts = await get_solved_alerts(client_id=client.id)
    if solved_alerts:
        logger.debug(f'For client id={client.id} get {len(solved_alerts)}')
        for alert in solved_alerts:
            client_template = await get_client_message_template(client_id=client.id)
            client_emoji = await get_client_emoji(client_id=client.id)
            alert_message = create_alert_message(alert_metrics=alert, template=client_template,
                                                 emoji=client_emoji)
            offset = timezone(timedelta(hours=3))
            alert_message = alert_message.replace('Сейчас', datetime.now(offset).strftime('%H:%M'))
            logger.debug(f'For client id={client.id} created solved alert message {alert_message}')
            send_message(message_text=alert_message, client=client, message_id=alert.message_id,
                         nosound=False,
                         alert_id=alert.id)
            await delete_solved_alert_from_database(client_id=client.id, alert_id=alert.id)
# end database functions


@logger.catch()
def create_alert_message(alert_metrics: AlertMessageArguments, template: str, emoji: ClientEmoji) -> str:
    """Создаём текст телеграм уведомления"""
    from string import Template
    template = Template(template)
    alert_metrics.importance = emoji.dict(by_alias=False).get(alert_metrics.importance)
    if alert_metrics.is_fast_detected:
        alert_metrics.is_fast_detected = emoji.is_fast_detected
    else:
        alert_metrics.is_fast_detected = ''
    message = template.substitute(alert_metrics.dict(by_alias=True))
    result = ''
    for line in message.split('\n'):
        if not 'None' in line:
            result = result + line + '\n'
    return result


@logger.catch()
async def get_alerts_from_arbor(client: ClientElement) -> List[ArborAlert]:
    import ssl
    sslcontext = ssl.create_default_context()
    sslcontext.check_hostname = False
    sslcontext.verify_mode = ssl.CERT_NONE
    sslcontext.set_ciphers('DEFAULT')
    search_filter = {'api_key': client.arbor_api_key, 'filter': client.filter, 'limit': '20'}
    result = []
    logger.debug(f'Start to get alerts for client {client.id}')
    timeout = aiohttp.ClientTimeout(total=20, connect=10)
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=sslcontext),
                                         timeout=timeout, trust_env=True) as session:
            async with session.post(client.url, params=search_filter) as resp:
                alerts = await resp.json()
                logger.debug(f'For client_id {client.id} got response: status={resp.status} data={alerts}')
                if len(alerts) > 0:
                    for alert in alerts:
                        result.append(ArborAlert.parse_obj(alert))
    except aiohttp.ServerTimeoutError as ex:
        logger.error(f'Timeout error with {client.url}! Returning ongoing for client {client.id}!')
        await keep_client_alerts_ongoing(client_id=client.id)
    except Exception as ex:
        logger.error(f'Got unexpected error with {client.url}. {ex.__class__.__module__}.{ex.__class__.__name__}: {ex}')
    finally:
        logger.debug(f'for client_id {client.id} got {len(result)} alerts {result}')
        return result


@logger.catch()
def prepare_alert(client: ClientElement, alert: ArborAlert) -> AlertMessageArguments:
    """Подготовить метрики алерта для записи в БД"""
    prepared_alert = AlertMessageArguments(chat_id=client.chat_id, label=client.label, alert_type=alert.alert_type,
                                           alert_id=alert.alert_id,
                                           is_fast_detected=alert.is_fast_detected,
                                           importance=alert.importance,
                                           duration=(alert.start + timedelta(hours=3)).strftime('%H:%M') + ' - Сейчас',
                                           ongoing=alert.ongoing,
                                           managed_object=alert.resource.managedObjects[0].name,
                                           ip=alert.resource.cidr,
                                           severity_pct=str(alert.severity_pct) + '%',
                                           bps=bps_formatted(alert.max_impact_bps),
                                           pps=pps_formatted(alert.max_impact_pps),
                                           misuseTypes=misuse_types_formatted(alert.misuseTypes), )
    return prepared_alert


def send_message(client: ClientElement, message_text: str, message_id: int, alert_id: int, nosound: bool):
    element = TelegramQueueElement(chat_id=client.chat_id, message_id=message_id, message_text=message_text,
                                   telegram_bot_api_token=client.telegram_bot_api_key, client_id=client.id,
                                   alert_id=alert_id, nosound=nosound)
    logger.debug(f'For client_id {client.id} send message {element.dict()}')
    import pika
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='telegram_bots')
    channel.basic_publish(exchange='', routing_key='telegram_bots', body=element.json())
    connection.close()


@logger.catch()
async def start_alerts_processing(client: ClientElement, alerts: List[ArborAlert]) -> None:
    for current_alert in alerts:
        if current_alert.max_impact_bps > client.no_alert_bps:
            saved_alert = await get_existing_alert_from_db(client_id=client.id, alert_id=current_alert.alert_id)
            prepared_alert = prepare_alert(client=client, alert=current_alert)
            if saved_alert:
                prepared_alert.message_id = saved_alert.message_id
                if saved_alert.dict(exclude={'message_id', 'ongoing'}) != prepared_alert.dict(exclude={'message_id', 'ongoing'}) or \
                        saved_alert.message_id < 0:
                    """обновить данные алерта в БД + отредактировать сообщение в телеге"""
                    logger.debug(
                        f'Alert alert_id={current_alert.alert_id} need to update \n{saved_alert}\n{prepared_alert}')
                    is_updated = await update_alert_in_in_db(client_id=client.id, alert=prepared_alert)
                    is_updated = await update_alert_ongoing_in_db(client_id=client.id, alert=prepared_alert)
                    client_template = await get_client_message_template(client_id=client.id)
                    client_emoji = await get_client_emoji(client_id=client.id)
                    alert_message = create_alert_message(alert_metrics=prepared_alert, template=client_template,
                                                         emoji=client_emoji)
                    logger.debug(f'For client id={client.id} created message {alert_message}')
                    send_message(message_text=alert_message, client=client, message_id=prepared_alert.message_id,
                                 nosound=(client.no_sound_bps > current_alert.max_impact_bps or
                                          client.no_sound_pps > current_alert.max_impact_pps),
                                 alert_id=prepared_alert.id)
                else:
                    """алерт не изменил метрики, сохраняем ongoing и идём дальше"""
                    logger.debug(f'''Alert alert_id={current_alert.alert_id} dont need to be updated
{saved_alert}\n{prepared_alert}''')
                    is_updated = await update_alert_ongoing_in_db(client_id=client.id, alert=prepared_alert)
            else:
                logger.debug(f'Alert alert_id={current_alert.alert_id} for client id={client.id} is new')
                """новый алерт, запишем в бд, отправим в телегу"""
                logger.debug(f'Got new alert for client {client.id}')
                await save_alert_in_database(client=client, alert=prepared_alert)
                client_template = await get_client_message_template(client_id=client.id)
                client_emoji = await get_client_emoji(client_id=client.id)
                alert_message = create_alert_message(alert_metrics=prepared_alert, template=client_template,
                                                     emoji=client_emoji)
                send_message(message_text=alert_message, client=client, message_id=prepared_alert.message_id,
                             nosound=(client.no_sound_bps > current_alert.max_impact_bps or
                                      client.no_sound_pps > current_alert.max_impact_pps),
                             alert_id=prepared_alert.id)
                logger.debug(f'For client id={client.id} created message {alert_message}')


@logger.catch()
async def client_main_function(client: ClientElement) -> None:
    await drop_client_alerts_ongoing(client_id=client.id)
    alerts = await get_alerts_from_arbor(client)
    if alerts:
        await asyncio.wait_for(start_alerts_processing(client=client, alerts=alerts), 30)
        await drop_solved_alerts(client=client)
    else:
        await drop_solved_alerts(client=client)


@logger.catch
async def main():
    try:
        await database.connect()

        while True:
            clients_list = await get_clients()
            logger.debug(f'Get list of clients: {clients_list}')
            tasks = []
            for client in clients_list:
                task = asyncio.create_task(client_main_function(client))
                tasks.append(task)
            await asyncio.wait_for(asyncio.gather(*tasks), 30)
            await asyncio.sleep(10)
    except Exception as ex:
        logger.error(f'Got an unexpected error {ex}')
        raise


@logger.catch()
async def exit_func():
    logger.debug('Exit')
    await database.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
