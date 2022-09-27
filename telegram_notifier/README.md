# Install Python 3.10

Бот находится на сервере bot-dev1.svcp.io
Состоит из 2 микросервисов:
1. Сам бот который опрашивает разные источники и производит обработку результатов
2. Сервис отправки и редактирования сообщений в телеграм
```bash
sudo apt install build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev libpq-dev python-dev -y
wget https://www.python.org/ftp/python/3.10.0/Python-3.10.0.tgz
mkdir .python3.10
tar -xf Python-3.10.*.tgz
cd Python-3.10.*/
./configure --enable-optimizations --prefix=/home/user/.python3.10
make -j 4
sudo make altinstall
cd ~/.python3.10/bin/
pwd
```
копируем `/home/user/.python3.10/bin`
```bash
cd ~
vim .bashrc
```
Вставляем в конец файла 

`export PATH=$PATH:/home/user/.python3.10/bin`
```bash
. ~/.bashrc
```

# How to deploy

```commandline
git init
git clone https://gitlab.svcp.io/kzhuravlev/arbor_bot.git
cd /cybertapi
```
```bash
python3.10 -m venv env
. env/bin/activate
pip install -r requirements.txt
```
Run command from project directory with activated virtual enviroment:
```bash
python main.py
python telegram_messages_sender.py
```
To deactivate virtual enviroment:
```bash
deactivate
```

# Apidoc service example for user <ins>www</ins>

```bash
cat /etc/systemd/system/arborbot.service 
[Unit]
Description=Arborbot cool version
After=network.target

[Service]
User=kzhuravlev
Group=www-data
WorkingDirectory=/home/kzhuravlev/arbor_bot
Environment="PATH=/home/kzhuravlev/arbor_bot/env/bin"
ExecStart=/home/kzhuravlev/arbor_bot/env/bin/python3.10 main.py
Restart=always
PIDFile=/home/kzhuravlev/arbor_bot/arb_ervice.pid

[Install]
WantedBy=multi-user.target
```
```bash
cat /etc/systemd/system/telegram_sender.service
[Unit]
Description=Telegram sender
After=network.target

[Service]
User=kzhuravlev
Group=www-data
WorkingDirectory=/home/kzhuravlev/arbor_bot
Environment="PATH=/home/kzhuravlev/arbor_bot/env/bin"
ExecStart=/home/kzhuravlev/arbor_bot/env/bin/python3.10 telegram_messages_sender.py
Restart=always
PIDFile=/home/kzhuravlev/arbor_bot/tg_service.pid

[Install]
WantedBy=multi-user.target
```
Start service:
```bash
sudo systemctl daemon-reload
sudo systemctl start arborbot.service
sudo systemctl start telegram_sender.service
```
# Таблицы БД
1. 