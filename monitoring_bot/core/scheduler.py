import json
from asyncio import sleep
import aiohttp
from core.models.database import alerts_db, database
from core.schemas.base_schemas import QueueElement, messages_queue
from core.settings import message_reties, message_sending_interval, logger


@logger.catch()
async def save_message_id(element: QueueElement, message_id: int):
    query = alerts_db.update().values(message_id=message_id).where(alerts_db.c.text == element.text,
                                                                   alerts_db.c.chat_id == element.chat_id)
    await database.execute(query)


@logger.catch()
async def telegram_messages_scheduler():
    while True:
        queue_element = await messages_queue.get()
        match queue_element.type.lower():
            case 'telegram':
                if queue_element.counter < message_reties:
                    logger.debug(queue_element)
                    if queue_element.message_id is None:
                        logger.debug(f'Inside telegram sending {queue_element}')
                        # Send new message to telegram
                        await send_message(queue_element)
                    elif queue_element.message_id > 0:
                        logger.debug(f'Inside telegram editing {queue_element}')
                        # Edit message text in telegram
                        await update_message(queue_element)
                    else:
                        pass
                    await sleep(message_sending_interval)
                else:
                    if queue_element.message_id > 0:
                        # Counter is above "message_reties" value, drop element
                        pass
                    elif queue_element.message_id is None:
                        # change message id because we cant edit message in future if we dont send message
                        await save_message_id(element=queue_element, message_id=-1)
                        pass
                    elif queue_element.message_id == -1:
                        # uneditable message, drop it
                        pass

            case 'sms':
                pass


@logger.catch()
async def update_message(queue_element: QueueElement):
    if queue_element.message_id > 0:
        try:
            base_url = f'https://api.telegram.org/bot{queue_element.telegram_bot_token}/editMessageText'
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                params = {'chat_id': queue_element.chat_id, 'text': queue_element.text, 'parse_mode': 'Markdown',
                          'message_id': queue_element.message_id}
                async with session.post(base_url, params=params) as resp:
                    text = await resp.json()
                    if resp.status == 200:
                        logger.debug(f'Editing status: {text}')
                    else:
                        logger.error(f'Cant edit message: {queue_element}, api error: {text}')
                        queue_element.counter = queue_element.counter + 1
                        await messages_queue.put(queue_element)
        except Exception as ex:
            queue_element.counter = queue_element.counter + 1
            logger.error(f'Cant edit message {queue_element} got unexpected error: {ex}')
    else:
        pass


@logger.catch()
async def send_message(queue_element: QueueElement):
    try:
        base_url = f'https://api.telegram.org/bot{queue_element.telegram_bot_token}/sendMessage'
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            params = {'chat_id': queue_element.chat_id, 'text': queue_element.text, 'parse_mode': 'Markdown',
                      'disable_notification': queue_element.nosound}
            async with session.post(base_url, params=params) as resp:
                text = await resp.json()
                if resp.status == 200:
                    message_id = text.get('result', dict()).get('message_id')
                    logger.debug(f'Sending status: {text}')
                    await save_message_id(element=queue_element, message_id=message_id)
                else:
                    logger.error(f'Cant send queue element: {queue_element}, api error: {text}')
                    queue_element.counter = queue_element.counter + 1
                    await messages_queue.put(queue_element)
    except Exception as ex:
        queue_element.counter = queue_element.counter + 1
        logger.error(f'Cant send message {queue_element}, got unexpected error: {ex}')
