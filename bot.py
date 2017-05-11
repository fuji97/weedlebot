import os
import re
import logging
import models
from models import DataCommandHandler, DataMessageHandler
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async
from loli import getFromAlgorithms
from telegram.error import TelegramError, Unauthorized

# Enable logging
logging.basicConfig(format='%(name)s - %(thread)d - %(message)s',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

# SETTINGS
COMMANDS = {
    "help": "Informazioni sull'utilizzo del bot",
    "loli": "Invia una loli casuale presa da Imgur",
    "regole": "Invia in privato le regole del gruppo"
}

# Env var
ROOT_URL =os.environ.get("ROOT_URL")
CHANNEL = int(os.environ.get("CHANNEL", 0))
OWNER = int(os.environ.get("ID_OWNER", 0))
FANGROUP = int(os.environ.get("ID_FAN_GROUP", 0))
CERT = os.environ.get("CERT")
KEY = os.environ.get("KEY")
POLLING = bool(os.environ.get("POLLING",False))
TOKEN = os.environ.get("TELEGRAM_KEY")
PORT = int(os.environ.get('PORT', '5000'))

def main():
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(DataCommandHandler("start", start))
    dp.add_handler(DataCommandHandler("help", help))
    dp.add_handler(DataCommandHandler("setup", setup))
    dp.add_handler(DataCommandHandler("loli", loli, pass_args=True))
    dp.add_handler(DataCommandHandler("register",register))
    dp.add_handler(DataCommandHandler("regole",rules))
    dp.add_handler(DataCommandHandler("commands",commands))
    dp.add_handler(DataMessageHandler(Filters.all,echo))

    # log all errors
    dp.add_error_handler(error)

    if POLLING:
        logger.info("Utilizzo del long polling")
        updater.bot.setWebhook("")
        updater.start_polling()
    else:
        logger.info("Utilizzo del webhook")
        updater.start_webhook(listen="0.0.0.0",
                            port=PORT,
                            url_path=TOKEN)
        updater.bot.setWebhook(ROOT_URL + "/" + TOKEN)
    updater.idle()

def start(bot, update, session):
    logger.info("Ricevuto comando start da: %s", update.message.from_user.username)
    models.registerUpdate(session, update)
    update.message.reply_text('C-Ciao Onii-san, sono la loli personale dei gruppo @weedlefan, se hai bisogno di supporto usa il comando /help o contatta il mio senpai @fuji97.',quote=False)

def chatId(bot, update, session):
    logger.info("Ricevuto comando chatId da: %s", update.message.from_user.username)
    data = models.registerUpdate(session, update)
    #if update.message.from_user.id == OWNER:
    if checkPermission(data['user'], 2, chat=data.chat):
        update.message.reply_text("Chat ID: " + str(update.message.chat_id),quote=False)
    else:
        update.message.reply_text("Scusa onii-san, ma non hai i permessi per usare questo comando :(",quote=False)

def setup(bot, update, session):
    logger.info("Ricevuto comando setup da: %s", update.message.from_user.username)
    data = models.registerUpdate(session, update)
    if checkPermission(data['user'], 1):
        models.createTables()
        update.message.reply_text("Tabelle del database aggiornate", quote="False")

def help(bot, update, session):
    logger.info("Ricevuto comando help da: %s", update.message.from_user.username)
    data = models.registerUpdate(session, update)
    if data['chat'].type == models.ChatType.private:
        update.message.reply_text("""Ciao onii-san, io sono Loli-chan!
Sono stata creata per essere usata principalmente in combinazione col gruppo @weedlefan e quindi molti comandi rispondono solo a quel gruppo.
Posso comunque essere utilizzata anche su altri gruppi con alcuni comandi generici, ti lascio la lista dei comandi:
Generici:
/loli - Manda una loli casuale cercata su Internet

Gruppo @weedlefan:
/regole - Invia in privato le regole del gruppo

Sono ancora in via di sviluppo, quindi tornate più avanti per vedere se ci sono nuove funzionalità!
Alla prossima Onii-san!""",quote=False)

def rules(bot, update, session):
    logger.info("Ricevuto comando rules da: %s [%s]", update.message.from_user.username, str(update.message.from_user.id))
    file = open("rules.html","r")
    text = ''.join(file.readlines())
    file.close()
    text = re.compile("\n!SPLIT!\n").split(text)
    try:
        for msg in text:
            bot.sendMessage(chat_id=update.message.from_user.id,text=msg,parse_mode="html")
    except Unauthorized:
        update.message.reply_text("<i>Per ricevere le regole abilitami in privato</i>",parse_mode="html",quote=False)

def commands(bot, update, session):
    logger.info("Ricevuto comando commands da: %s", update.message.from_user.username)
    data = models.registerUpdate(session, update)
    if checkPermission(data['user'], 1):
        items = COMMANDS.items()
        text = ""
        for item in items:
            text += item[0] + " - " + item[1] + "\n"
        update.message.reply_text(text,quote=False)

# Disattivato, usato solo per scopi di debug
def register(bot, update, session):
    logger.info("Ricevuto comando register da: %s", update.message.from_user.username)
    models.registerUpdate(session, update)


def echo(bot, update, session):
    data = models.registerUpdate(session, update)
    if update.channel_post != None:
        logger.info("Ricevuto post dal canale: [%s]", str(update.channel_post.chat_id))
        if update.channel_post.chat_id == CHANNEL:
            logger.info("Messaggio ricevuto dal canale, inoltro nel fangroup con citazione")
            update.channel_post.forward(FANGROUP)
    else:
        logger.info("Ricevuto testo da: %s [%s]", update.message.from_user.username, str(update.message.from_user.id))
        if checkPermission(data['user'], 3):
            logger.info("Messaggio ricevuto dall'owner, inoltro nel fangroup")
            mess = update.message
            if mess.sticker != None:
                bot.sendSticker(chat_id=FANGROUP, sticker=mess.sticker.file_id)
            elif mess.video != None:
                bot.sendVideo(chat_id=FANGROUP, video=mess.video.file_id, duration=mess.video.duration, caption=mess.caption)
            elif mess.voice != None:
                bot.sendVoice(chat_id=FANGROUP, voice=mess.voice.file_id, duration=mess.voice.duration, caption=mess.caption)
            elif mess.audio != None:
                bot.sendVoice(chat_id=FANGROUP, audio=mess.audio.file_id, duration=mess.audio.duration, caption=mess.caption, performer=mess.audio.performer, title=mess.audio.title)
            elif mess.photo:
                bot.sendPhoto(chat_id=FANGROUP, photo=mess.photo[0].file_id, caption=mess.caption)
            elif mess.document != None:
                bot.sendDocument(chat_id=FANGROUP, document=mess.document.file_id, file_name=mess.document.file_name, caption=mess.caption)
            elif mess.text != '':
                bot.sendMessage(chat_id=FANGROUP, text=mess.text, parse_mode="markdown")
            else:
                logger.warning("Messaggio invalido ricevuto dall'owner")

def loli(bot, update, args, session):
    logger.info("Ricevuto comando loli da: %s con parametri %s",
                update.message.from_user.username, ' '.join(args))
    data = models.registerUpdate(session, update)

    if len(args) > 0:
        try:
            count = int(args[0])
            logger.info("Richiesto invio di %i immagini con parametro %s",
                        count, ' '.join(args[1:]))
            if 0 < count <= 10 and checkPermission(data['user'], 4, chat=data['chat']):
                param = ' '.join(args[1:]) if not '' else None
                for i in range(0, count):
                    sendImage(update, models.Session(), param)
            else:
                logger.info("Numero di immagini oltre il limite o mancanza di permessi")
        except ValueError:
            param = ' '.join(args)
            logger.info("Richiesta loli con parametro di ricerca: %s", param)
            sendImage(update, session, param)
    else:
        sendImage(update, session)


@run_async
def sendImage(update, session, param=None):
    logging.debug("sendImage avviato")
    image = getFromAlgorithms(session, param)
    logger.debug("Immagine ricevuta, invio su Telegram")
    if image["gif"]:
        update.message.reply_video(video=image["link"],quote=False)
    else:
        update.message.reply_photo(photo=image["link"],quote=False)
    logger.debug("Chiusura del thread di sendImage")

def error(bot, update, error):
    logger.warn('Update "%s" ha causato un errore "%s"' % (update, error))

def checkPermission(user, level, chat=None):
    if user.id == OWNER:
        return True
    if chat:
        role = next(member for member in chat.users if member.user == user).user_role
        if role.value <= level:
            return True
        else:
            return False
    else:
        if user.general_role.value <= level:
            return True
        else:
            return False

if __name__ == '__main__':
    updater = Updater(TOKEN)
    main()
    logger.info("Uscita in corso...")
