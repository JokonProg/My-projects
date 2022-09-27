from app import API_TOKEN, URL_BASE
import telebot
import time


bot = telebot.TeleBot(API_TOKEN)
bot.remove_webhook()
time.sleep(1)
bot.set_webhook(url=URL_BASE)

