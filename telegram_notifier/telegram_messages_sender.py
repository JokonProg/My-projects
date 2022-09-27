from telegram_queue_models import TelegramQueueElement
import pika, sys, os
from time import sleep
import telebot
from telebot.apihelper import ApiTelegramException
from loguru import logger
from pika.exceptions import AMQPConnectionError


log_dir = 'logs/'
log_file = 'telegram_messages.log'
log_level = 'debug'
log_retention = '2 days'
logfile = log_dir + log_file
logger.remove()
logger.add(logfile, format='{time} [{level}] {message}', level=log_level.upper(),
           rotation='00:00', compression='zip', backtrace=True, retention=log_retention)


def write_message_id_in_database(client_id: int, alert_id: int, message_id: int):
    from database import engine
    from database.models import db_active_alerts
    connection = engine.connect()
    query = db_active_alerts.update().values(message_id=message_id).where(db_active_alerts.c.client_id == client_id,
                                                                          db_active_alerts.c.alert_id == alert_id)
    connection.execute(query)
    connection.close()


def send_to_telegram(query_element: TelegramQueueElement) -> None:
    bot = telebot.TeleBot(query_element.telegram_bot_api_token, threaded=False)
    if query_element.message_id <= 0:
        try:
            logger.debug(f'Try to send element to telegram')
            message = bot.send_message(chat_id=query_element.chat_id, text=query_element.message_text,
                                       disable_notification=query_element.nosound, parse_mode='markdown')
            write_message_id_in_database(client_id=query_element.client_id, alert_id=query_element.alert_id,
                                         message_id=message.message_id)
            logger.debug(f'Sending success')
        except ApiTelegramException as ex:
            logger.error(
                f"Got an exception with sending message {ex.description} with alert_id={query_element.alert_id}")
            write_message_id_in_database(client_id=query_element.client_id, alert_id=query_element.alert_id,
                                         message_id=-1)
        except ConnectionError as ex:
            logger.error(f'Got an ConnectionError with sending message {ex.description}')
            write_message_id_in_database(client_id=query_element.client_id, alert_id=query_element.alert_id,
                                         message_id=-1)
        except Exception as ex:
            logger.critical(f'Got unexpected error with sending message {query_element.client_id=}. {ex.__class__.__module__}.{ex.__class__.__name__}: {ex}')
            write_message_id_in_database(client_id=query_element.client_id, alert_id=query_element.alert_id,
                                         message_id=-1)
    else:
        try:
            logger.debug(f'Try to edit message in telegram')
            bot.edit_message_text(text=query_element.message_text, chat_id=query_element.chat_id,
                                  message_id=query_element.message_id, parse_mode='markdown')
        except ApiTelegramException as ex:
            logger.error(f'Got an exception with editing message {ex.description}')
        except ConnectionError as ex:
            logger.error(f'Got an ConnectionError with editing message {ex.description}')
        except Exception as ex:
            logger.critical(f'Got unexpected error with editing message {query_element.client_id=}. {ex.__class__.__module__}.{ex.__class__.__name__}: {ex}')


def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='telegram_bots')

    def callback(ch, method, properties, body):
        query_element = TelegramQueueElement.parse_raw(body)
        query_element.message_text = query_element.message_text.replace('_', '\_')
        logger.debug(f'Got element from query: {query_element}')
        send_to_telegram(query_element)

        sleep(1)

    channel.basic_consume(queue='telegram_bots', on_message_callback=callback, auto_ack=True)

    channel.start_consuming()


if __name__ == '__main__':
    try:
        main()
    except AMQPConnectionError as ex:
        logger.critical(f'Got an error with connecting to rabbit. {ex.__class__.__module__}.{ex.__class__.__name__}: {ex}')
        sleep(20)
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

