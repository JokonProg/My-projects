import datetime
import os
import psycopg2
from psycopg2.extras import DictCursor


# postgres variables {
PG_PORT = os.environ['PG_PORT']
PG_DB_NAME = os.environ['PG_DB_NAME']
PG_DB_USER = os.environ['PG_DB_USER']
PG_DB_PASSWORD = os.environ['PG_DB_PASSWORD']
# }
cursor = None


def read_conn_to_db_decorator(func):
    def setup_connect(*args, **kwargs):
        global cursor
        conn = psycopg2.connect(dbname=PG_DB_NAME, user=PG_DB_USER, password=PG_DB_PASSWORD, host='localhost',
                                port=6432)
        cursor = conn.cursor(cursor_factory=DictCursor)
        result = func(*args, **kwargs)
        cursor.close()
        conn.close()
        return result

    return setup_connect


def write_conn_to_db_decorator(func):
    def setup_connect(*args, **kwargs):
        global cursor
        conn = psycopg2.connect(dbname=PG_DB_NAME, user=PG_DB_USER, password=PG_DB_PASSWORD, host='localhost',
                                port=6432)
        cursor = conn.cursor(cursor_factory=DictCursor)
        result = func(*args, **kwargs)
        conn.commit()
        cursor.close()
        conn.close()
        return result

    return setup_connect


@write_conn_to_db_decorator
def create_chat_in_db(datetime: str, chat_id: int, chat_title: str) -> str:
    global cursor
    cursor.execute("""SELECT chat_id from telegram_chats where chat_id=%s;""",
                   (chat_id,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute("""INSERT INTO telegram_chats (start_from, chat_id, chat_title, chat_type, locale, last_activity) 
                        VALUES (%s, %s, %s, 'client', 'EN', %s);""", (datetime, chat_id, chat_title, datetime,))
        return 'Done'
    elif result[0] == chat_id:
        return 'Chat {} already exist'.format(str(chat_id))


@write_conn_to_db_decorator
def add_user_in_db(user_id: str, name: str, role: str) -> str:
    global cursor
    cursor.execute("""SELECT user_id from telegram_users where user_id=%s;""",
                   (user_id,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute("""INSERT INTO telegram_users (user_id, name, role) VALUES (%s, %s, %s);""",
                       (user_id, name, role,))
        return 'Done'
    elif result[0] == user_id:
        return 'User %s already exist' % user_id


@read_conn_to_db_decorator
def select_list_users_from_db() -> str:
    global cursor
    cursor.execute("""SELECT * from telegram_users;""")
    result = cursor.fetchall()
    answer = ' id, name, role\n'
    for line in result:
        answer = answer + '%(id)s, %(name)s, %(role)s\n' % {'id': line.get('user_id'),
                                                            'name': line.get('name'),
                                                            'role': line.get('role')}
    return answer


@write_conn_to_db_decorator
def delete_user_from_db(user_id: str) -> str:
    global cursor
    cursor.execute("""SELECT user_id from telegram_users where user_id=%s;""",
                   (user_id,))
    result = cursor.fetchone()
    if result is None:
        return 'User %s not found' % user_id
    elif result[0] == user_id:
        cursor.execute("""DELETE FROM telegram_users WHERE user_id=%s;""", (user_id,))
        return 'Done'


@read_conn_to_db_decorator
def get_type_of_user(user_id: str) -> str:
    global cursor
    cursor.execute("""SELECT role from telegram_users where user_id=%s;""",
                   (user_id,))
    result = cursor.fetchone()
    if result is None:
        return False
    else:
        return result['role']


@read_conn_to_db_decorator
def get_list_chats_from_db() -> str:
    global cursor
    cursor.execute("""SELECT chat_id, chat_title, chat_type, last_activity from telegram_chats""")
    result = cursor.fetchall()
    answer = ' chat_id, chat_title, chat_type, last_activity\n'
    for line in result:
        answer = answer + '%(id)s, %(title)s, %(type)s, %(last_activity)s\n' % {'id': line.get('chat_id'),
                                                                                'title': line.get('chat_title'),
                                                                                'type': line.get('chat_type'),
                                                                                'last_activity': line.get(
                                                                                    'last_activity')}
    return answer


@write_conn_to_db_decorator
def edit_chat_type_in_db(chat_id: int, type_chat: str) -> str:
    global cursor
    cursor.execute("""SELECT chat_id, chat_type from telegram_chats where chat_id=%s;""",
                   (chat_id,))
    result = cursor.fetchone()
    if result != None:
        if result['chat_type'] != type_chat:
            cursor.execute("""UPDATE telegram_chats SET chat_type=%s where chat_id=%s;""", (type_chat, chat_id))
            return 'Done'
        else:
            return 'Done'
    else:
        return 'Chat ID not exist in DB. Try /start at first.'


@write_conn_to_db_decorator
def make_admin_to_exist_user_in_db(user_id: str) -> str:
    global cursor
    cursor.execute("""SELECT user_id from telegram_users where user_id=%s;""", (user_id,))
    result = cursor.fetchone()
    if result is None:
        return 'Unknown user %s. Try to /addNewSupporter or /addNewSales at first' % user_id
    elif result[0] == user_id:
        cursor.execute("UPDATE telegram_users SET role='admin' where user_id=%s;", (user_id,))
        return 'Done'


@write_conn_to_db_decorator
def delete_chat_from_db(chat_id: int) -> str:
    global cursor
    cursor.execute("""SELECT chat_id from telegram_chats where chat_id=%s;""",
                   (chat_id,))
    result = cursor.fetchone()
    if result is None:
        return ('Chat %s not found' % str(chat_id))
    elif result[0] == chat_id:
        cursor.execute("""DELETE FROM telegram_chats WHERE chat_id=%s;""", (chat_id,))
        return 'Done'


@write_conn_to_db_decorator
def update_activity(chat_id: str, datetime: str):
    global cursor
    cursor.execute("""SELECT chat_id from telegram_chats where chat_id=%s;""", (chat_id,))
    result = cursor.fetchone()
    if result is not None and result[0] == chat_id:
        cursor.execute("""UPDATE telegram_chats SET last_activity=%s where chat_id=%s;""", (datetime, chat_id,))


@write_conn_to_db_decorator
def update_chat_id_in_db(chat_id: int, new_chat_id: int) -> bool:
    global cursor
    cursor.execute("""SELECT chat_id from telegram_chats where chat_id=%s;""", (chat_id,))
    result = cursor.fetchone()
    if result[0] == chat_id:
        cursor.execute("""UPDATE telegram_chats SET chat_id=%s where chat_id=%s;""", (new_chat_id, chat_id,))
        cursor.execute("""UPDATE subscribed_tickets SET chat_id=%s where chat_id=%s;""", (new_chat_id, chat_id,))
        return True
    else:
        return False


@write_conn_to_db_decorator
def update_chat_title_in_db(chat_id: int, new_title: str) -> str:
    cursor.execute("""SELECT chat_id from telegram_chats where chat_id=%s;""", (chat_id,))
    result = cursor.fetchone()
    if result['chat_id'] == chat_id:
        cursor.execute("""UPDATE telegram_chats SET chat_title=%s where chat_id=%s;""", (new_title, chat_id,))
        return 'Chat %s title updated to ```%s```' % (str(chat_id), new_title)


@write_conn_to_db_decorator
def check_chat_in_db(chat_id: int, permission_level: str) -> bool:
    global cursor
    cursor.execute("""SELECT chat_id from telegram_chats where chat_id=%s and chat_type=%s;""",
                   (chat_id, permission_level))
    result = cursor.fetchone()
    if result[0] == chat_id:
        return True
    else:
        return False


@read_conn_to_db_decorator
def get_id_notify_chat(type) -> int:
    cursor.execute("""SELECT chat_id from telegram_chats where chat_type=%s;""", (type,))
    result = cursor.fetchone()
    return int(result['chat_id'])


@read_conn_to_db_decorator
def get_type_of_current_chat(id:int) -> int:
    cursor.execute("""SELECT chat_type from telegram_chats where chat_id=%s;""", (id,))
    result = cursor.fetchone()
    return str(result['chat_type'])


@read_conn_to_db_decorator
def check_user_in_db(user_id: str, permission_level) -> bool:
    global cursor
    if permission_level:
        cursor.execute("""SELECT user_id from telegram_users where user_id=%s and role=%s;""",
                       (user_id, permission_level,))
        result = cursor.fetchone()
        if result:
            return True
        else:
            return False
    else:
        return True


@write_conn_to_db_decorator
def update_activity(message: str):
    global cursor
    cursor.execute("""SELECT chat_id from telegram_chats where chat_id=%s;""",
                   (int(dict(dict(message.get('message')).get('chat')).get('id')),))
    result = cursor.fetchone()
    if result is not None and result[0] == int(dict(dict(message.get('message')).get('chat')).get('id')):
        cursor.execute("""UPDATE telegram_chats SET last_activity=%s where chat_id=%s;""",
                       (str(datetime.datetime.fromtimestamp(dict(message.get('message')).get('date'))),
                        int(dict(dict(message.get('message')).get('chat')).get('id')),))


@write_conn_to_db_decorator
def subscribe_ticket_in_db(chat_id: int, ticket_id: str) -> bool:
    global cursor
    cursor.execute("""INSERT INTO subscribed_tickets (chat_id, ticket_id, status) 
                        VALUES (%s, %s, 'in progress');""", (chat_id, ticket_id,))
    return True


@write_conn_to_db_decorator
def delete_ticket_in_db(ticket_id: str):
    global cursor
    cursor.execute("""DELETE FROM subscribed_tickets WHERE ticket_id=%s;""", (ticket_id,))


@read_conn_to_db_decorator
def print_subscribed_tickets_from_db(chat_id: int) -> str:
    global cursor
    cursor.execute("""SELECT ticket_id, status from subscribed_tickets where chat_id=%s;""", (chat_id,))
    result = cursor.fetchall()
    answer = ' Active tickets:\n'
    for line in result:
        answer = answer + '%(id)s - %(status)s\n' % {'id': line.get('ticket_id'), 'status': line.get('status')}
    return answer


@read_conn_to_db_decorator
def get_chat_id_from_ticket_id(ticket_id: str):
    global cursor
    cursor.execute("""SELECT chat_id from subscribed_tickets where ticket_id=%s;""", (ticket_id,))
    result = cursor.fetchall()
    return result
