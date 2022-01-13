import asyncio
import aiohttp
from aiohttp.client_exceptions import ClientConnectorError
import json
from core.models.database import DATABASE_URL, alerts_db, metadata, database
from sqlalchemy import create_engine
from sqlalchemy.exc import CompileError
from core.schemas.database_schemas import AlertIn
from core.schemas.base_schemas import ArborElement, ClientElement, Importance, QueueElement, messages_queue, \
    MessageStatus
from typing import Optional, List
from datetime import timedelta, datetime
import ssl
from core.scheduler import telegram_messages_scheduler
from core.settings import alerts_recheck_interval, ignore_managed_objects, logger

sslcontext = ssl.create_default_context()
sslcontext.set_ciphers('AES256-GCM-SHA384')
sslcontext.check_hostname = False
sslcontext.verify_mode = ssl.CERT_NONE

engine = create_engine(
    DATABASE_URL, pool_size=3, max_overflow=0
)
# metadata.drop_all(engine) # use if you want to recreate database with program restart
metadata.create_all(engine)


@logger.catch()
async def main():
    await database.connect()
    scheduler_task = telegram_messages_scheduler()
    asyncio.ensure_future(scheduler_task)
    while True:
        with open("clients.json", mode="r") as file:
            text = file.read()
            clients = json.loads(text)
            tasks = list()
            for client in clients:
                ext = ClientElement(**client)
                task = asyncio.create_task(alert_main_function(ext))
                tasks.append(task)
            await asyncio.gather(*tasks)
            await asyncio.sleep(alerts_recheck_interval)


@logger.catch()
async def alert_main_function(client: ClientElement) -> None:
    await drop_ongoing(client)
    alerts = await get_arbor_alerts(client)
    for alert in alerts:
        notify_message = create_base_notify_message(client=client, alert=alert)
        if any(managed_object in notify_message for managed_object in ignore_managed_objects) \
                or alert.max_impact_bps < client.no_alert_bps:
            pass
        else:
            need_to_send = MessageStatus(await is_need_to_sent(client=client, alert=alert, text=notify_message))
            logger.debug(f'{(client.no_sound_pps < alert.max_impact_pps)} and {(client.no_alert_bps < alert.max_impact_bps)}')
            nosound = (client.no_sound_pps < alert.max_impact_pps) and (client.no_alert_bps < alert.max_impact_bps) or \
                      False
            match need_to_send:
                case need_to_send.SEND:
                    logger.debug(f'Need to send\n{notify_message}\n\n')
                    query = alerts_db.insert().values(alert_id=alert.id, ongoing=True,
                                                      managed_object=alert.resource.managedObjects[0].name,
                                                      client_type=client.type, client_name=client.name,
                                                      client_label=client.label, chat_id=client.chat_id,
                                                      text=notify_message)
                    await database.execute(query)
                    queue_element = QueueElement(type=client.type, text=notify_message, chat_id=client.chat_id,
                                                 counter=0, telegram_bot_token=client.bot, nosound=nosound)
                    await messages_queue.put(queue_element)
                case need_to_send.UPDATE:
                    logger.debug(f'Need update\n{notify_message}\n\n')
                    await update_alert_message(client=client, alert=alert, text=notify_message)
                    message_id = await get_message_id(client=client, alert=alert)
                    logger.debug(f'Message_id = {message_id}')
                    queue_element = QueueElement(type=client.type, text=notify_message, chat_id=client.chat_id,
                                                 counter=0, telegram_bot_token=client.bot, message_id=message_id)
                    await messages_queue.put(queue_element)
                case need_to_send.SKIP:
                    logger.debug(f"Don't need sending or update\n{notify_message}\n\n")
                    await keep_alert_ongoing(client=client, alert=alert, text=notify_message)
    messages = await get_finished_alerts(client=client)
    for message in messages:
        message.text = message.text.replace('Сейчас', datetime.now().strftime('%H:%M'))
        logger.debug(f"Solved alerts: \n{message.text}\n\n")
        queue_element = QueueElement(type=client.type, text=message.text, chat_id=message.chat_id, counter=0,
                                     message_id=message.message_id, telegram_bot_token=client.bot)
        await messages_queue.put(queue_element)
    await delete_finished_alerts(client)


def create_base_notify_message(client: ClientElement, alert: ArborElement) -> str:
    text = f"""*[{client.label}] {alert.type} №{alert.id}*
{importance_format(alert.importance)}{fast_flood_format(alert.is_fast_detected)}
*Клиент:* {alert.resource.managedObjects[0].name}
*Трафик:* {pps_format(alert.max_impact_pps)} / {bps_format(alert.max_impact_bps)}
*Время:* {datetime_formatting(alert.start)} - Сейчас
*IP-адрес: {alert.resource.cidr}*
*Превышение порогов:* {alert.severity_pct}%
*Тип:* {attack_type_formatting(alert.misuseTypes)}"""
    return text


def datetime_formatting(alert_datetime: datetime) -> str:
    moscow_time = alert_datetime + timedelta(hours=3)
    return moscow_time.strftime('%H:%M')


def attack_type_formatting(types: Optional[str]) -> str:
    if types and len(types) > 1:
        return ', '.join(types)
    elif types and len(types) == 1:
        return types[0]
    else:
        return 'None'


def importance_format(importance: Importance) -> str:
    match importance:
        case importance.HIGH:
            return '\U0001F534 *Высокая*'
        case importance.MEDIUM:
            return '\U0001F7E1 *Средняя*'
        case importance.LOW:
            return '\U0001F7E2 *Низкая*'


def fast_flood_format(fast_flood):
    match fast_flood:
        case True:
            return ' \U0001F525 *Fast Flood*'
        case False:
            return ''


def pps_format(pps):
    if pps < 1000:
        return '%i' % pps + ' pps'
    elif 1000 <= pps < 1000000:
        return '%.1f' % float(pps / 1000) + ' Kpps'
    elif 1000000 <= pps < 1000000000:
        return '%.1f' % float(pps / 1000000) + ' Mpps'
    elif 1000000000 <= pps < 1000000000000:
        return '%.1f' % float(pps / 1000000000) + ' Gpps'
    elif 1000000000000 <= pps:
        return '%.1f' % float(pps / 1000000000000) + ' Tpps'


def bps_format(bps):
    if bps < 1000:
        return '%i' % bps + ' bps'
    elif 1000 <= bps < 1000000:
        return '%.1f' % float(bps / 1000) + ' Kbps'
    elif 1000000 <= bps < 1000000000:
        return '%.1f' % float(bps / 1000000) + ' Mbps'
    elif 1000000000 <= bps < 1000000000000:
        return '%.1f' % float(bps / 1000000000) + ' Gbps'
    elif 1000000000000 <= bps:
        return '%.1f' % float(bps / 1000000000000) + ' Tbps'


@logger.catch()
async def get_arbor_alerts(client: ClientElement) -> list:
    result = []
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=sslcontext),
                                         timeout=timeout) as session:
            headers = {'api_key': client.api_key, 'filter': client.filter, 'limit': '20'}
            async with session.post(client.url, params=headers) as resp:
                text = await resp.text()
                if resp.status == 200:
                    logger.debug(f'Get alerts: {text}')
                    for alert in json.loads(text):
                        result.append(ArborElement(**alert))
                    return result
                else:
                    raise ConnectionRefusedError
    except ConnectionRefusedError:
        logger.warning(f'Connection refused {client.url}')
        await keep_client_alerts_ongoing(client=client)
        return result
    except ClientConnectorError:
        logger.warning(f'ClientConnectorError {client.url}')
        await keep_client_alerts_ongoing(client=client)
        return result
    except asyncio.exceptions.TimeoutError:
        logger.warning(f'Timeout Error {client.url}')
        await keep_client_alerts_ongoing(client=client)
        return result
    except Exception as ex:
        logger.error(ex)
        await keep_client_alerts_ongoing(client=client)
        return result


@logger.catch()
async def save_alert(alert: ArborElement) -> bool:
    query = alerts_db.insert().values(alert.dict())
    try:
        await database.execute(query)
        return True
    except CompileError as ex:
        logger.warning(ex)
        return False


@logger.catch()
async def keep_client_alerts_ongoing(client: ClientElement) -> None:
    query = alerts_db.update().values(ongoing=True).where(alerts_db.c.client_type == client.type,
                                                          alerts_db.c.client_name == client.name,
                                                          alerts_db.c.client_label == client.label,
                                                          alerts_db.c.chat_id == client.chat_id)
    await database.execute(query)


@logger.catch()
async def update_alert_message(client: ClientElement, alert: ArborElement, text: str) -> None:
    query = alerts_db.update().values(text=text, ongoing=True).where(alerts_db.c.client_type == client.type,
                                                                     alerts_db.c.client_name == client.name,
                                                                     alerts_db.c.client_label == client.label,
                                                                     alerts_db.c.chat_id == client.chat_id,
                                                                     alerts_db.c.alert_id == alert.id)
    await database.execute(query)


@logger.catch()
async def keep_alert_ongoing(client: ClientElement, alert: ArborElement, text: str) -> None:
    query = alerts_db.update().values(ongoing=True).where(alerts_db.c.client_type == client.type,
                                                          alerts_db.c.client_name == client.name,
                                                          alerts_db.c.client_label == client.label,
                                                          alerts_db.c.chat_id == client.chat_id,
                                                          alerts_db.c.alert_id == alert.id,
                                                          alerts_db.c.text == text)
    await database.execute(query)


@logger.catch()
async def drop_ongoing(client: ClientElement) -> None:
    query = alerts_db.update().values(ongoing=False).where(alerts_db.c.client_type == client.type,
                                                           alerts_db.c.client_name == client.name,
                                                           alerts_db.c.client_label == client.label,
                                                           alerts_db.c.chat_id == client.chat_id)
    await database.execute(query)


@logger.catch()
async def get_finished_alerts(client: ClientElement) -> Optional[List[AlertIn]]:
    query = alerts_db.select().where(alerts_db.c.client_type == client.type,
                                     alerts_db.c.client_name == client.name,
                                     alerts_db.c.client_label == client.label,
                                     alerts_db.c.chat_id == client.chat_id,
                                     alerts_db.c.ongoing == False)
    alerts = await database.fetch_all(query)
    result = list()
    if alerts:
        for alert in alerts:
            alert = AlertIn(**alert)
            result.append(alert)
        return result
    else:
        return alerts


@logger.catch()
async def delete_finished_alerts(client: ClientElement) -> None:
    query = alerts_db.delete().where(alerts_db.c.client_type == client.type,
                                     alerts_db.c.client_name == client.name,
                                     alerts_db.c.client_label == client.label,
                                     alerts_db.c.chat_id == client.chat_id,
                                     alerts_db.c.ongoing == False)
    await database.execute(query)


@logger.catch()
async def is_need_to_sent(client: ClientElement, alert: ArborElement, text: str) -> str:
    query = alerts_db.select().where(alerts_db.c.chat_id == client.chat_id,
                                     alerts_db.c.client_type == client.type,
                                     alerts_db.c.alert_id == alert.id)
    result = await database.fetch_one(query)
    if result:
        result = AlertIn(**result)
        if text == result.text:
            return 'skip'
        else:
            return 'update'
    else:
        return 'send'


@logger.catch()
async def get_message_id(client: ClientElement, alert: ArborElement) -> Optional[int]:
    query = alerts_db.select().where(alerts_db.c.chat_id == client.chat_id,
                                     alerts_db.c.client_type == client.type,
                                     alerts_db.c.alert_id == alert.id,
                                     alerts_db.c.managed_object == alert.resource.managedObjects[0].name)
    result = await database.fetch_one(query)
    if result:
        result = AlertIn(**result)
        return result.message_id
    else:
        return None


try:
    if __name__ == "__main__":
        asyncio.run(main())
except KeyboardInterrupt:
    logger.debug('Program closed')
