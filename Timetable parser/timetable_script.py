from requests_toolbelt.multipart.encoder import MultipartEncoder
from bs4 import BeautifulSoup
import json
import requests
import logging
import sys

URL = 'https://api.vk.com/method/wall.post?'
DATA = {'owner_id': '<vk_id>',
       'from_group': '1',
       'message': 'test',
       'access_token': '<vk_token>>',
       'v': '5.70'}


def save_rasp(filename, data):
    print("save_rasp")
    try:
        with open(filename, mode='w', encoding='utf-8') as output_file:
            json.dump(data, output_file, ensure_ascii=False)
            logger.info("Timetable saved")
    except Exception:
        logger.error("Timetable not saved : %s" % sys.exc_info()[1])



def get_raspisanie ():
    url = 'https://mf.mfua.ru/studentu/raspisanie.php'
    multipart_data = MultipartEncoder(fields={'q3': '3906'})
    try:
        req = requests.post(url, data=multipart_data, headers={'Content-Type': multipart_data.content_type}, verify=False)
        logger.info("POST request succeed")
        return req.text
    except Exception:
        logger.error("Cant get timetable: %s " % sys.exc_info()[1])
        sys.exit()


def check_changes(timetable):
    try:
        timetable_old = open(saved_rasp, mode='r', encoding='utf-8')
        try:
            tmp = json.load(timetable_old)
        except Exception:
            logger.info("Timetable is require to change(%s)" % sys.exc_info()[1])
            return True
        else:
            if timetable == tmp:
                logger.info("Timetable not require to change")
                return False
            else:
                logger.info("Timetable is require to change")
                return True
        timetable_old.close()
    except FileNotFoundError:
        logger.info("File 'saved_rasp.txt' not fount.")
        return True
    except Exception:
        logger.error("Cant get timetable: %s" % sys.exc_info()[1])

def post_timetable(tmtbl):
    try:
        date = ''
        output = ''
        for line in tmtbl:
            if date != line['date']:
                date = line['date']
                output = output + line['date'] + '\n'
            output = output + line['time'] + ' : ' + line['name'] + ' : ' + line['prep'] + ' : ' + line['aud'] + ' : ' + line['type'] + '\n'
        DATA['message'] = output
        try:
            responce = requests.post(URL, data=DATA)
            print('Ответ: ' + responce.text)
        except Exception:
            print('Ошибка :' + str(sys.exc_info()[0]))
    except Exception:
        logger.error("Couldn't parse file " % sys.exc_info()[1])



logger = logging.getLogger("raspisanieApp")
logger.setLevel(logging.INFO)
logfile = logging.FileHandler("bot.log")
formatter = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s')
logfile.setFormatter(formatter)
logger.addHandler(logfile)


predmet = {
    'date': '',
    'time': '',
    'name': '',
    'prep': '',
    'aud': '',
    'type': ''
}

saved_rasp = "saved_rasp.txt"
logger.info("Start program")
soup = BeautifulSoup(get_raspisanie(), 'html.parser')
tree = soup.find('table', {'border': '1'})
results = []
tr = tree.find_all('tr', {'': ''})
for item in tr[1:]:
    i = 1
    td = item.find_all('td')
    for p in td:
        tmp = ""
        tmp1 = p.findNext('p').text
        if i == 1:
            predmet['date'] = str(tmp1).strip()
        elif i == 2:
            predmet['time'] = str(tmp1).strip()
        elif i == 3:
            predmet['name'] = str(tmp1).strip()
        elif i == 4:
            predmet['prep'] = str(tmp1).strip()
        elif i == 5:
            predmet['aud'] = str(tmp1).strip()
        elif i == 6:
            predmet['type'] = str(tmp1).strip()
        i += 1
    if predmet['date'] != predmet['time']:
        results.append(predmet.copy())
logger.info("Timetable is update?")
if (check_changes(results)):
    save_rasp(saved_rasp, results)
    post_timetable(results)

logger.info("Program closed")