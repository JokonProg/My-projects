from db_fuctions import *
from flask import Blueprint
from jira import JIRA, JIRAError
import os
import time


# jira variables {
JIRA_LOGIN = os.environ['JIRA_LOGIN']
JIRA_TOKEN = os.environ['JIRA_TOKEN']
JIRA_URL = os.environ['JIRA_URL']
JIRA_OPTIONS = {'server': JIRA_URL}
# }
jira_blueprint = Blueprint('jira', __name__)
jira = JIRA(options=JIRA_OPTIONS, basic_auth=(JIRA_LOGIN, JIRA_TOKEN))


MESSAGE_UPDATE = '''Ticket already updated
%(key)s:%(summary)s
%(fieldId)s: %(fromString)s -> %(toString)s
by %(displayName)s
https://variti.atlassian.net/browse/%(key)s'''
UPDATER = {'key': '', 'summary': '', 'fieldId': '', 'fromString': '', 'toString': '', 'displayName': ''}
MESSAGE_CREATE = '''Ticket created
%(key)s:%(summary)s
Reporter: %(reporter)s
Assigned to: %(assigned)s
https://variti.atlassian.net/browse/%(key)s'''
CREATOR = {'key': '', 'summary': '', 'reporter': '', 'assigned': ''}


formatter = """`{}: {}`
   Status: *{}*
   Assigned: _{}_ {}
   Link: https://variti.atlassian.net/browse/{}

   """
limit_len = 4096
smile_adder = {'<name>': '💩',
               '<name2>': '💃'}

notify_chat_id = get_id_notify_chat('jira')


@jira_blueprint.route('/fiofah7Ohmegieferai3bao6go8ue8Ei', methods=['POST'])
def jira_webhook_handler():
    import flask
    import json
    from app import send_notification_to_group
    temp = json.loads(flask.request.get_data())
    if temp['webhookEvent'] == 'jira:issue_updated':
        UPDATER['key'] = temp['issue'].get('key')
        UPDATER['summary'] = temp['issue']['fields']['summary']
        UPDATER['fieldId'] = dict(temp['changelog']['items'][0])['fieldId']
        UPDATER['fromString'] = dict(temp['changelog']['items'][0])['fromString']
        UPDATER['toString'] = dict(temp['changelog']['items'][0])['toString']
        UPDATER['displayName'] = temp['user']['displayName']
        output = MESSAGE_UPDATE % UPDATER
        send_notification_to_group(chat=notify_chat_id, msg=output)
        field = str(UPDATER['fieldId']).lower()
        cur_state = str(UPDATER['toString'])
        ticket_id = str(UPDATER['key'])
        if field == 'resolution' and cur_state == 'Done':
            chats = get_chat_id_from_ticket_id(ticket_id=ticket_id)
            message = 'Ticket {} closed.'.format(ticket_id)
            for chat in chats:
                time.sleep(1)
                id = int(chat['chat_id'])
                send_notification_to_group(chat=id, msg=message)
            delete_ticket_in_db(ticket_id=UPDATER['key'])
        return ('{"success": "ok"}')
    else:
        if temp['webhookEvent'] == 'jira:issue_created':
            CREATOR['key'] = temp['issue'].get('key')
            CREATOR['summary'] = temp['issue']['fields']['summary']
            CREATOR['assigned'] = temp['issue']['fields']['assignee']['displayName']
            CREATOR['reporter'] = temp['issue']['fields']['reporter']['displayName']
            output = MESSAGE_CREATE % CREATOR
            send_notification_to_group(chat=notify_chat_id, msg=output)
            return ('{"success": "ok"}')


def check_ticket(issueKey: str):
    issueKey = issueKey.strip('/')
    jql = 'issueKey = {}'.format(issueKey)
    try:
        results = jira.search_issues(jql)
        for issue in results:
            if str(issue.fields.resolution) != 'Done':
                return True
            else:
                return '[ERROR] Ticket solved'
    except JIRAError:
        return '[ERROR] Ticket not exist'


def get_active_tickets():
    from app import send_notification_to_group
    output = ''
    JQL = '''project = IASUP AND issuetype = Task AND status not in ("Can't reproduce", Deferred, Duplicate, "In Deploy", "In Review", "Will Not Fix", Done) order by created ASC'''
    for issue in jira.search_issues(JQL):
        smile = smile_adder.get(str(issue.fields.assignee), '')
        string = str(
            formatter.format(issue.key, issue.fields.summary, issue.fields.status, issue.fields.assignee, smile,
                             issue.key))
        if len(output) + len(string) >= limit_len:
            send_notification_to_group(chat=notify_chat_id, msg=output)
            output = string
            time.sleep(1)
        else:
            output = output + string
    send_notification_to_group(chat=notify_chat_id, msg=output)
