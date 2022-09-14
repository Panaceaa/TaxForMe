# coding=utf-8
import datetime
from telegram.ext import Updater, filters
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler
from telegram import ParseMode
import re
import time
import db_update
import data_graph


token = '2009637863:AAGafdSiceD-U2qGFw5RxWyh3TOofZ_W-mY'
updater = Updater(token, use_context=True)
START = 'Привет!😊 Введи тикер акции о которой хочешь узнать больше.'
product = 'taxforme'


def start(update, context):
    chat_id = update.message.chat.id
    updater.bot.send_message(chat_id=chat_id, text=START)
    db_update.user_data((update.message.chat.username, update.message.chat.first_name, int(update.message.chat.id), product))


def user_answer(update, context):
    chat_id = update.message.chat.id
    user = update.message.chat.first_name
    user_name = update.message.chat.username
    db_update.user_data((user_name, user, int(chat_id), product))
    symbol = update.message.text
    pattern = '[a-zA-z]'
    symbol = ''.join(x for x in re.findall(pattern, symbol)).upper()
    name = data_graph.fmp_name(symbol)
    if name is not None:
        context.user_data['ticker'] = symbol
        updater.bot.send_message(chat_id=chat_id, text=f'Найдена компания: <b>{name}</b>\n\nУкажи дату покупки в формате как эта: 01.01.2021', parse_mode=ParseMode.HTML)

    else:
        db_update.user_error(chat_id, symbol, update.message.date, product='taxforme')
        updater.bot.send_message(chat_id=chat_id, text='Тикер не найден 😿\n\nВ нашей базе только акции, торгующиеся на NYSE или Nasdaq')


def user_date(update, context):
    chat_id = update.message.chat.id
    date_response = time.mktime(update.message.date.timetuple())

    try:
        start_date = datetime.datetime.strptime(update.message.text, '%d.%m.%Y')

        db_update.response_data((chat_id, context.user_data['ticker'], start_date, date_response, product))
        z, t, cur, pr, ret = data_graph.return_usd_rub([context.user_data['ticker']], [start_date])
        advice = '<b>Совет:</b> Если рассчитываешь доходность в долларах, сейчас лучшее время для фиксирования прибыли, в рублях - стоит подождать увеличение курса рубля.'

        if float(z[5][:-1]) >= float(z[5][:-1]):
            advice = '<b>Совет:</b> Если рассчитываешь доходность в долларах, то стоит подождать снижение курса рубля, в рублях - лучшее время для фиксирования прибыли.'

        if float(z[5][:-1]) <= 0 and float(z[5][:-1]) <= 0:
            advice = 'Доходности нет, изменение курса никак не влияет на результат'
        updater.bot.send_message(chat_id=chat_id, text=
                            f'\n{"📈" if float(re.sub("[%]", "", z[4])) >= 0 else "📉"} <b>Доходность: {z[4]}</b>\n\n{"📈" if float(re.sub("[%]", "", z[5])) >= 0 else "📉"} <b>C учетом курса: {z[5]}</b>\n\n{"📈" if float(re.sub("[%]", "", z[6])) >= 0 else "📉"} <b>C учетом курса после налогов: {z[6]}</b>\n\n • Последняя цена акции: {z[2]}\n\n • Последний курс USDRUB: {z[3]}\n\n📊 Таблица ниже может показать, что будет с доходностью в рублях после налогов если курс вырастет/упадет на 3%, или акция вырастет/упадет на 10%.\n\n<b>Как понять таблицу:</b> Если курс увеличится до {cur}, а цена акции останется на отметке {pr}, то доходность после налогов составит: {ret}\n\n{advice}\n<em>(Не является индивидуальной инвестиционной рекомендацией.)</em>',
                            parse_mode=ParseMode.HTML)
        updater.bot.send_message(chat_id=chat_id, text=t, parse_mode=ParseMode.HTML)

    except Exception:
        updater.bot.send_message(chat_id=chat_id, text="Неверный формат даты 😾\n\nПопробуй ещё раз.")


def quit_func(update, context):
    return ConversationHandler.END


TICKER = 0

updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(MessageHandler(filters.Filters.regex('[a-zA-z]'), callback=user_answer))
updater.dispatcher.add_handler(MessageHandler(filters.Filters.regex('\.') & (~ filters.Filters.command), callback=user_date))

updater.start_polling()


