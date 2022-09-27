from flask import *
import logging
import pymysql
from pymysql.cursors import DictCursor
import sys


app = Flask(__name__)


def open_connection():
  """Opening connection to MySQL database"""
  try:
    connect = pymysql.connect(
      host='localhost',
      user='root',
      password='',
      db='ippier_test2',
      charset='utf8',
      cursorclass=DictCursor
    )
  except Exception:
    logger.error("Error: %s" % sys.exc_info()[1])
    sys.exit()
  else:
    return connect


@app.route('/app/help_bot/command/<command>', methods=['POST'])
def create_command(command):
  logger.info("Get command api 'create_command'")
  if command is None or request.form.get('description') is None:
    logger.error("Invalid request")
    abort(400)
  if len(command) == 0 or len(request.form.get('description')) == 0:
    logger.error("Invalid request")
    abort(400)
  else:
    desc=request.form.get('description')
    connection = open_connection()
    cursor = connection.cursor()
    req = """insert into help_commands (name, description) values ('%s', '%s')""" % (command, desc)
    try:
      cursor.execute(req)
      logger.info("Created command '%s'" % command)
    except Exception:
      logger.error(sys.exc_info()[1])
      abort(400, sys.exc_info()[1])
    else:
      connection.commit()
      connection.close()
      return jsonify({'success': 'ok'})

@app.route('/app/help_bot/command/<command>', methods=['PUT'])
def edit_command(command):
  logger.info("Get command api 'edit_comand'")
  if command is None or request.form.get('description') is None:
    logger.error("Invalid request")
    abort(400)
  if len(command) == 0 or len(request.form.get('description')) == 0:
    logger.error("Invalid request")
    abort(400)
  else:
    connection = open_connection()
    cursor = connection.cursor()
    req = """update help_commands set description='%s' where name='%s'""" % (request.form.get('description'), command)
    try:
      cursor.execute(req)
    except Exception:
      logger.error(sys.exc_info()[1])
      abort(400, sys.exc_info()[1])
    else:
      connection.commit()
      connection.close()
      logger.info("Edited command '%s'" % command)
      return jsonify({'success': 'ok'})



@app.route('/app/help_bot/commands/', methods = ['GET'])
def return_commands():
  logger.info("Get api command 'return_commands'")
  connection = open_connection()
  cursor = connection.cursor()
  req = """select name, description from help_commands order by id"""
  try:
    cursor.execute(req)
  except Exception:
    logger.error(sys.exc_info()[1])
    abort(400, sys.exc_info()[1])
  else:
    result = cursor.fetchall()
    connection.close()
    logger.info("List of commands returned")
    return jsonify(result)

@app.route('/app/help_bot/command/<command>', methods = ['GET'])
def return_command(command):
  if command is None:
    logger.error("Invalid request 'command' = '%s'" % command)
    abort(400)
  if len(command) == 0:
    logger.error("Invalid request 'command' lenght = '%s'" % str(len(command)))
    abort(400)
  else:
    logger.info("Get api command 'return_command' = %s" % command)
    connection = open_connection()
    cursor = connection.cursor()
    req = """select name, description from help_commands where name = '%s'""" % command
    try:
      cursor.execute(req)
    except Exception:
      logger.error(sys.exc_info()[1])
      abort(400, sys.exc_info()[1])
    else:
      result = cursor.fetchone()
      connection.close()
      return jsonify(result)

@app.route('/app/help_bot/command/<command>', methods = ['DELETE'])
def delete_command(command):
  if command is None:
    logger.error("Invalid request 'command' = '%s'" % command)
    abort(400)
  if len(command) == 0:
    logger.error("Invalid request 'command' lenght = '%s'" % str(len(command)))
    abort(400)
  else:
    logger.info("Delete command - %s" % command)
    connection = open_connection()
    cursor = connection.cursor()
    req = """delete from help_commands where name = '%s'""" % command
    try:
      cursor.execute(req)
    except Exception:
      logger.error(sys.exc_info()[1])
      abort(400, sys.exc_info()[1])
    else:
      connection.commit()
      connection.close()
      logger.info("Command '%s' deleted" % command)
      return jsonify({'success': 'ok'})



if __name__ == '__main__':
  log_file = "rest_api.log"
  logger = logging.getLogger("help_command_api")
  logger.setLevel(logging.INFO)
  logfile = logging.FileHandler(log_file)
  formatter = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s')
  logfile.setFormatter(formatter)
  logger.addHandler(logfile)
  app.run(port=8011)
