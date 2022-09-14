import psycopg2

PROD_DATABASE_URI = "host=35.228.5.243 dbname='postgres' user='postgres' password='f4wlB3iOhha1HgF1'"
conn = psycopg2.connect(PROD_DATABASE_URI)
cur = conn.cursor()


def response_data(row):
    cur.execute(
        """INSERT INTO taxforme.telegram_response (chat_id, ticker, start_date, response_date_unix, product) 
           VALUES (%s, %s, %s, %s, %s);""", row)
    conn.commit()


def user_data(row):
    try:
        cur.execute("""SELECT * FROM taxforme.telegram_users""")
    except Exception:
        conn.rollback()
    try:
        data = cur.fetchall()
    except Exception:
        data = None
    if not data:
        pass
    else:
        users = [x[2] for x in data]
        product = [x[3] for x in data]
        if row[2] in users and row[3] in product:
            return
        cur.execute("""INSERT INTO taxforme.telegram_users (username, user_nick, chat_id, product) 
                       VALUES (%s, %s, %s, %s);""", row)
        conn.commit()


def telegram_data_request(chat_id):
    cur.execute(f"""SELECT * FROM taxforme.telegram_data WHERE chat_id = {chat_id}""")
    return cur.fetchall()


def user_connection(chat_id, connected):
    try:
        cur.execute(f"""INSERT INTO taxforme.telegram_data (chat_id, connected) VALUES (%s, %s)""",
                    (chat_id, connected))
        conn.commit()
    except:
        conn.rollback()


def telegram_update_data(chat_id, data, value):
    cur.execute(f"UPDATE taxforme.telegram_data SET {data} = '{value}' WHERE chat_id = {chat_id}")
    conn.commit()


def clear_user(chat_id):
    cur.execute(f"DELETE FROM taxforme.telegram_data portfolio_description WHERE chat_id = {chat_id}")
    conn.commit()


def rollback():
    cur.execute("ROLLBACK")
    conn.commit()


def user_error(chat_id, ticker, request_time, product='taxforme'):
    try:
        cur.execute(f"""INSERT INTO taxforme.telegram_users (chat_id, ticker, request_time, product) VALUES (%s, %s, %s, %s)""",
                    (chat_id, ticker, request_time, product))
        conn.commit()
    except:
        conn.rollback()
