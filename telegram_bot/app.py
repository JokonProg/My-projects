from jira_functions import *
from db_fuctions import *
import flask
import json
import os
import re
import telebot


# telegram variables {
API_TOKEN = os.environ['API_TOKEN']
URL_BASE = os.environ['URL_BASE']
BOT_ID = os.environ['BOT_ID']
# }

bot = telebot.TeleBot(API_TOKEN)
app = flask.Flask(__name__)
app.register_blueprint(jira_blueprint)


@app.route('/chaiquienee7Ikeedohd9sheF1ieKaer', methods=['POST'])
def telegram_webhook_handler():
    json_string = flask.request.get_data().decode('utf-8')
    a = json.loads(json_string)
    if flask.request.headers.get('content-type') == 'application/json':
        update_activity(a)
        if dict(a.get('message')).get('new_chat_title'):
            rename_chat(a)
        if dict(a.get('message')).get('migrate_to_chat_id'):
            migrate_chat(a)
        update = telebot.types.Update.de_json(json_string)
        try:
            bot.process_new_updates([update])
            time.sleep(1)
            bot.send_message(chat_id=1064541153, text=json_string)
        except Exception:
            bot.send_message(chat_id=1064541153, text=json_string)
    return ''


@bot.message_handler(commands=['start'])
def start_chat_reaction(message):
    """```/start```
Input current chat as allowed to database
Allowed chat types: all
Allowed user types: admin, support, sales"""
    if auth_user(message, 'admin') or auth_user(message, 'support') or auth_user(message, 'sales'):
        date_time = str(datetime.datetime.fromtimestamp(message.date))
        id = int(message.chat.id)
        title = str(message.chat.title)
        result = create_chat_in_db(datetime=date_time, chat_title=title, chat_id=id)
        bot.send_message(chat_id=message.chat.id, text=result)


@bot.message_handler(commands=['stop'])
def stop_chat_reaction(message):
    """```/stop```
Input current chat as allowed to database
Allowed chat types: all
Allowed user types: admin, support"""
    if auth_user(message, 'admin') or auth_user(message, 'support') or auth_user(message, 'sales'):
        answer = delete_chat_from_db(chat_id=message.chat.id)
        bot.send_message(chat_id=message.chat.id, text=answer)


@bot.message_handler(commands=['chatID'])
def send_chat_id(message):
    """```/chatID```
Returns chat_id
Allowed chat types: all
Allowed user types: all"""
    bot.send_message(chat_id=message.chat.id, text=message.chat.id)


@bot.message_handler(commands=['myID'])
def my_id_command(message):
    """```/myID```
Return user_id
Allowed chat types: all
Allowed user types: all"""
    bot.send_message(chat_id=message.chat.id, text=message.from_user.id)


@bot.message_handler(regexp='/addNewSupporter\s[0-9-]*\s[A-Za-z0-9_]*')
def add_supporter_command(message):
    """```/addNewSupporter <user_id> <name>```
to get user_id use ```/myID``` command
Allowed chat types: tech
Allowed user types: admin"""
    if auth_chat(message, 'tech') and auth_user(message, 'admin'):
        userID = str(message.text.split(' ')[1])
        user_name = str(message.text.split(' ')[2])
        answer = add_user_in_db(user_id=userID, name=user_name, role='support')
        bot.send_message(chat_id=message.chat.id, text=answer)


@bot.message_handler(regexp='/deleteUser\s[0-9]*')
def delete_user_command(message):
    """```/deleteUser <user_id>```
deleting user from database.
To get exist users use ```/listUsers```
Allowed chat types: tech
Allowed user types: admin"""
    if auth_chat(message, 'tech') and auth_user(message, 'admin'):
        userID = str(message.text.split(' ')[1])
        answer = delete_user_from_db(user_id=userID)
        bot.send_message(chat_id=message.chat.id, text=answer)


@bot.message_handler(regexp='/addNewSales\s[0-9]*\s[A-Za-z0-9_]*')
def add_sales_command(message):
    """```/addNewSales <user_id> <name>```
to get user_id use ```/myID``` command
Allowed chat types: tech
Allowed user types: admin, support"""
    if auth_chat(message, 'tech') and (auth_user(message, 'admin') or auth_user(message, 'support')):
        userID = str(message.text.split(' ')[1])
        user_name = str(message.text.split(' ')[2])
        answer = add_user_in_db(user_id=userID, name=user_name, role='sales')
        bot.send_message(chat_id=message.chat.id, text=answer)


@bot.message_handler(regexp='/giveAdmin\s[0-9]*')
def make_admin_to_exist_user(message):
    """```/giveAdmin <user_id>```
Grand admin privileges to user in DB.
Need to ```/addNewSupporter <user_id>``` or ```/addNewSales <user_id>``` at first.
Allowed chat types: tech
Allowed user types: admin"""
    if auth_chat(message, 'tech') and auth_user(message, 'admin'):
        userID=str(message.text.split(' ')[1])
        answer = make_admin_to_exist_user_in_db(user_id=userID)
        bot.send_message(chat_id=message.chat.id, text=answer)


@bot.message_handler(regexp='/man *')
def send_doc_string(message):
    if (auth_user(message, 'admin') or auth_user(message, 'support')) and auth_chat(message, 'tech'):
        if message.text.split(' ')[1]:
            command = str(message.text.split(' ')[1]).lower()
            answer = str(realised_commands.get(command, None))
            bot.send_message(chat_id=message.chat.id, text=answer, parse_mode='markdown')


@bot.message_handler(commands=['getPrivileges'])
def send_bot_privileges_in_current_chat(message):
    """```/getPrivileges```
Returning chat privileges for bot
Allowed chat types: client
Allowed user types: admin"""
    if auth_chat(message, 'client') and auth_user(message, 'admin'):
        answer = bot.get_chat_member(chat_id=message.chat.id, user_id=BOT_ID)
        bot.send_message(chat_id=message.chat.id, text=str(answer))


#@bot.message_handler(commands=['getMyPrivileges'])
#def send_user_privileges_in_current_chat(message):
#    """```/getMyPrivileges```
#Returning chat privileges for current user
#Allowed chat types: tech
#Allowed user types: admin"""
#    answer = bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)
#    bot.send_message(chat_id=message.chat.id, text=str(answer))


@bot.message_handler(commands=['listUsers'])
def print_users(message):
    """```/listUsers```
Show known users from DB with rules.
Allowed chat types: tech
Allowed user types: admin, support"""
    if auth_chat(message, 'tech') and (auth_user(message, 'admin') or auth_user(message, 'support')):
        answer = select_list_users_from_db()
        bot.send_message(chat_id=message.chat.id, text='```' + answer + '```', parse_mode='markdown')


@bot.message_handler(commands=['listChats'])
def print_confirmed_chats(message):
    """```/listChats```
Prints list of chats from the DB.
Allowed chat types: tech
Allowed user types: admin"""
    if auth_chat(message, 'tech') and (auth_user(message, 'admin') or auth_user(message, 'support')):
        answer = get_list_chats_from_db()
        bot.send_message(chat_id=message.chat.id, text='```' + answer + '```', parse_mode='markdown')


@bot.message_handler(regexp='/deleteChat\s[0-9-]*')
def delete_chat(message):
    """```/deleteChat <chat_id>```
Deleting chat from DB. Messages to this chat will be ignored.
To show 'chat_id' use command ```/listChats```
Allowed chat types: tech
Allowed user types: admin"""
    if auth_chat(message, 'tech') and auth_user(message, 'admin'):
        chatID = int(message.text.split(' ')[1])
        answer = delete_chat_from_db(chat_id=chatID)
        bot.send_message(chat_id=message.chat.id, text=answer)


@bot.message_handler(regexp='/setChatType\s[0-9-]*\s(?:client|tech|notify|jira)')
def edit_chat_type(message):
    """```/setChatType <chat_id> <client|tech|notify|jira>```
Set type of mentioned chat.
List of available commands may be different for each of types.
Allowed chat types: tech
Allowed user types: admin, support"""
    if (auth_user(message, 'admin') or auth_user(message, 'support')) and auth_chat(message, 'tech'):
        typeChat = str(message.text.split(' ')[2])
        chatID = int(message.text.split(' ')[1])
        result = edit_chat_type_in_db(chat_id=chatID, type_chat=typeChat)
        bot.send_message(chat_id=message.chat.id, text=result)


@bot.message_handler(regexp='/setType\s(?:client|tech|notify|jira)')
def edit_current_chat_type(message):
    """```/setType <client|tech|notify|jira>```
Set type of current chat.
List of available commands may be different for each of types.
Allowed chat types: client
Allowed user types: admin, support"""
    if (auth_user(message, 'admin') or auth_user(message, 'support')) and auth_chat(message, 'client'):
        typeChat = str(message.text.split(' ')[1])
        chatID = int(message.chat.id)
        result = edit_chat_type_in_db(chat_id=chatID, type_chat=typeChat)
        bot.send_message(chat_id=message.chat.id, text=result)


@bot.message_handler(regexp='/IASUP-[0-9]*')
def subscribe_chat_to_ticket(message):
    """```/IASUP-<number>```
Subscription to status update notifications. A ticket closure notification will be sent to subscribed chats.
Allowed chat types: client
Allowed user types: admin, support"""
    if (auth_user(message, 'admin') or auth_user(message, 'support')) and auth_chat(message, 'client'):
        status_ticket = check_ticket(str(message.text))
        if status_ticket == True :
            if subscribe_ticket_in_db(chat_id=int(message.chat.id), ticket_id=str(message.text).strip('/')):
                bot.send_message(chat_id=message.chat.id, text='Done')
        else:
            bot.send_message(chat_id=message.chat.id, text=status_ticket)


@bot.message_handler(commands=['getActive'])
def print_active_tickets(message):
    """```/getActive```
Print list of active issues in JIRA
Allowed chat types: client, jira
Allowed user types: all"""
    if get_type_of_current_chat(id=message.chat.id) == 'jira':
        get_active_tickets()
    else:
        result = print_subscribed_tickets_from_db(chat_id=message.chat.id)
        bot.send_message(chat_id=message.chat.id, text='```' + result + '```', parse_mode='markdown')


@bot.message_handler(commands=['help'])
def print_list_of_available_commands(message):
    user_type = get_type_of_user(user_id=str(message.from_user.id))
    ch_type = get_type_of_current_chat(id=message.chat.id)
    if user_type:
        help_msg = create_help_message(chat_type=ch_type, user_role=user_type)
    else:
        help_msg = create_help_message(chat_type=ch_type)
    bot.send_message(chat_id=message.chat.id, text='```' + help_msg + '```', parse_mode='markdown')


def rename_chat(message):
    id = int(dict(dict(message.get('message')).get('chat')).get('id'))
    title = str(dict(message.get('message')).get('new_chat_title'))
    answer = update_chat_title_in_db(chat_id=id, new_title=title)
    bot.send_message(chat_id=1064541153, text=answer, parse_mode='markdown')


def migrate_chat(message):
    chat_id = int(dict(dict(message.get('message')).get('chat')).get('id'))
    new_chat_id = int(dict(message.get('message')).get('migrate_to_chat_id'))
    result = update_chat_id_in_db(chat_id=chat_id, new_chat_id=new_chat_id)
    if result:
        msg = 'Chat {} migrated to new chat_id {}'.format(chat_id, new_chat_id)
        send_notification(msg)
    else:
        send_notification('something wrong')


def auth_chat(message, permission_level):
    chat_id = int(message.chat.id)
    result = check_chat_in_db(chat_id=chat_id, permission_level=permission_level)
    return result


def auth_user(message, permission_level=None):
    user_id = str(message.from_user.id)
    result = check_user_in_db(user_id=user_id, permission_level=permission_level)
    return result


def send_notification(message):
    bot.send_message(chat_id=1064541153, text=message)


def send_notification_to_group(chat: int, msg: str):
    bot.send_message(chat_id=chat, text=msg, parse_mode='Markdown')


def create_help_message(chat_type: str, user_role=None) -> str:
    answer = '\n'
    for line in realised_commands.values():
        res_chat = re.search(r'(?<=Allowed chat types: ).*(?=all|{})'.format(chat_type), line)
        res_client = re.search(r'(?<=Allowed user types: ).*(?={}|all)'.format(user_role), line)
        if res_client and res_chat:
            answer = answer + line.split('```')[1] + '\n'
    return answer


realised_commands = {'start': start_chat_reaction.__doc__,
                     'stop': stop_chat_reaction.__doc__,
                     'myid': my_id_command.__doc__,
                     'chatid': send_chat_id.__doc__,
                     'addnewsupporter': add_supporter_command.__doc__,
                     'deleteuser': delete_user_command.__doc__,
                     'addnewsales': add_sales_command.__doc__,
                     'giveadmin': make_admin_to_exist_user.__doc__,
                     'getprivileges': send_bot_privileges_in_current_chat.__doc__,
                     #'getmyprivileges': send_user_privileges_in_current_chat.__doc__,
                     'listusers': print_users.__doc__,
                     'listchats': print_confirmed_chats.__doc__,
                     'deletechat': delete_chat.__doc__,
                     'setchattype': edit_chat_type.__doc__,
                     'settype': edit_current_chat_type.__doc__,
                     'iasup': subscribe_chat_to_ticket.__doc__,
                     'getactive': print_active_tickets.__doc__}


if __name__ == '__main__':
    app.run()
