#!/usr/bin/env python
# -*- coding: utf-8 -*-
from uuid import uuid4
from telegram import InlineQueryResultCachedSticker
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, InlineQueryHandler
import logging
import psycopg2
import re


# Create connection to DB
conn = psycopg2.connect("dbname=<DBNAME> user=<USER> password=<PASSWORD>")
cur = conn.cursor()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

UPLOADSTICKER, TAGS = range(2)
ASK, ANSWER = range(2)

sticker_id = None

def start(bot, update):
    """Sends a message on startup"""
    update.message.reply_text("""Welcome to the sticker bot! Please reply with /add or /help""")

def help(bot, update):
    """Sends a help message"""
    update.message.reply_text("Please send /add to add a new sticker. Use @[botname] <tag(s)> inline to search")

def search(bot, update):
    """Searches and retrieves stickers matching given tags"""
    update.message.reply_text("Send me tags [separated by commas WITHOUT SPACES] to search!")

    return ASK

# TODO: Add inline search in bot convo
def query(bot, update):
    """Asks user what tags they want to search for"""
    tags = update.message.text
    tagList = tags.split(",")
    # remove duplicate tags
    tagList = list(set(tagList))

    for tag in tagList:
        cur.execute("""SELECT id FROM sticker_ids WHERE tags='{0}'""".format(tag))
        results = cur.fetchall()
        results = [tup[0] for tup in results]
        for result in results:
            bot.send_sticker(update.message.chat_id, result)
        else:
            update.message.reply_text("No result for your query, try again!")

    logger.info("Completed sending stickers")

    return ConversationHandler.END

def add(bot, update):
    """Walks a user through adding a new sticker"""
    # TODO: Prevent duplicate additions

    update.message.reply_text("Alright, send me the sticker you'd like me to add!")

    return UPLOADSTICKER

def sticker(bot, update):
    """Sticker uploading"""
    global sticker_id
    sticker_id = update.message.sticker.file_id
    #cur.execute("""INSERT INTO sticker_ids (id) VALUES ('%s');""" % str(sticker_id))
    bot.send_sticker(update.message.chat_id, sticker_id)
    update.message.reply_text("This is the sticker you sent")
    logger.info("Sticker id is: %s", sticker_id)
    update.message.reply_text('Okay, now give it some tags! \n'
                              '[Please separate tags with a comma, and NO SPACES!]')

    return TAGS

def tags(bot, update):
    text = update.message.text
    tagtext = text.split(",")
    tList = []
    for tag in tagtext:
        valid = re.sub(r"[^A-Za-z]+", '', tag)
        tList.append(valid)

    tagtext = list(set(tList))
    logger.info((sticker_id, text))
    for x in range(len(tagtext)):
        cur.execute("""INSERT INTO sticker_ids(id, tags) VALUES ('{0}', '{1}');""".format(sticker_id, tagtext[x]))
    conn.commit()
    text = "Okay, your tags were: " + text
    bot.sendMessage(update.message.chat_id, text, 'HTML')
    update.message.reply_text("Sticker successfully added.")
    logger.info("Tags passed were: %s", update.message.text)
    logger.info(update.message.from_user)

    return ConversationHandler.END

def inlinequery(bot, update):
    """Handle inline queries"""
    # TODO: prevent duplicate query tags and results

    query = update.inline_query.query
    querytags = query.split(",")
    qList = []
    for tag in querytags:
        valid = re.sub(r"[^A-Za-z]+", '', tag)
        qList.append(valid)

    # remove duplicate tags
    querytags = list(set(qList))
    logger.info(querytags)

    results = []
    file_ids = []
    #if query == 'showall':
        #cur.execute("""SELECT id FROM sticker_ids""")
        #ids = cur.fetchall()
        #ids = [tup[0] for tup in ids]
        #for id in ids:
            #if id in file_ids:
            #    pass
            #else:
                #results.append(InlineQueryResultCachedSticker(type='sticker', id=uuid4(), sticker_file_id=id))
                #file_ids.append(id)"""

    #else:
    for tag in querytags:
        cur.execute("""SELECT id FROM sticker_ids WHERE tags='{0}'""".format(tag))
        ids = cur.fetchall()
        ids = [tup[0] for tup in ids]
        for id in ids:
            if id in file_ids:
                pass
            else:
                results.append(InlineQueryResultCachedSticker(type='sticker', id=uuid4(), sticker_file_id=id))
                file_ids.append(id)
    else:
        pass

    logger.info(results)

    update.inline_query.answer(results)


def cancel(bot, update):
    update.message.reply_text("Alright! You can always upload later anyways!")

    return ConversationHandler.END

def error(bot, update, error):
    """Log errors"""
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    """Starts the bot"""
    # Create EventHandler and pass it bot token
    updater = Updater("BOT_TOKEN_GOES_HERE")

    # Get dispatcher to register handlers
    dp = updater.dispatcher

    # Conversation handler for adding stickers
    addhandler = ConversationHandler(
        entry_points=[CommandHandler('add', add)],

        states={
            UPLOADSTICKER: [MessageHandler(Filters.sticker, sticker)],
            TAGS: [MessageHandler(Filters.text, tags)]
            },

        fallbacks=[CommandHandler('cancel', cancel)]

    )

    # Conversation handler for searching for stickers
    searchhandler = ConversationHandler(
        entry_points=[CommandHandler('search', search)],

        states={
            ASK: [MessageHandler(Filters.text, query)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]

    )

    # Commands
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(addhandler)
    #dp.add_handler(searchhandler)
    dp.add_handler(InlineQueryHandler(inlinequery))

    # Log all errors
    dp.add_error_handler(error)

    # Start the bot
    updater.start_polling()

    updater.idle()

# Run the bot
if __name__ == '__main__':
    main()