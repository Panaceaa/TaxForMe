import datetime
import requests
import pandas as pd
import psycopg2
import json


def conn_barbacane():
    conn_config = {
        "dbname": "postgres",
        "user": "postgres",
        "host": "35.228.5.243",
        "password": "f4wlB3iOhha1HgF1",
        "schema": "taxforme"
    }

    schema = conn_config['schema']
    conn = psycopg2.connect(
        dbname=conn_config['dbname'],
        user=conn_config['user'],
        host=conn_config['host'],
        password=conn_config['password'],
        options=f'-c search_path={schema}',
    )
    return conn


conn = conn_barbacane()
cur = conn.cursor()


def fmp_prices(ticker, st_dt):
    api = '5999b507aa89f166a3682af1b59cf185'
    url = f'https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?from={st_dt}&apikey={api}'
    response = requests.get(url)

    try:
        json_table = json.loads(response.text)

        if not json_table:
            return None
        else:
            df = pd.DataFrame([(x['adjClose'], pd.to_datetime(x['date'])) for x in json_table['historical']],
                               columns=['adj_close_price', 'date'])
            df.loc[:, 'ticker'] = ticker
            return df
    except Exception:
        return None


def fmp_name(ticker):
    api = '5999b507aa89f166a3682af1b59cf185'
    url = f'https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={api}'
    response = requests.get(url)

    try:
        json_table = json.loads(response.text)

        if not json_table:
            return None
        else:
            return json_table[0]['companyName']
    except Exception:
        return None


def return_portfolio(returns, stocks):
    stocks = [int(x) for x in stocks]
    for i, column in enumerate(returns.columns):
        returns[column] = returns[column] * stocks[i]

    returns = returns.resample('D').ffill().ffill()

    returns = returns.sum(axis=1)
    return returns


def recommendation(price_r, price_u, entry):
    if price_r > entry >= price_u:
        return 'Не продавать (нет прибыли есть налог)'
    elif price_r <= entry < price_u:
        return 'Продавать (есть прибыль нет налога)'
    elif entry <= price_u < price_r:
        return 'Держать (налог больше ставки)'
    elif entry < price_r <= price_u:
        return 'Продавать (налог меньше ставки)'
    elif entry >= price_u >= price_r:
        return 'Держать (нет прибыли)'
    elif entry >= price_r >= price_u:
        return 'Держать (нет прибыли)'


def divide(x, y):
    try:
        return x / y
    except ZeroDivisionError:
        return 0


def matrix_data(pr2, cur2, pr1, cur1):
    tax = 0.87
    cur_mult = 0.03
    pr_mult = 0.1
    x = (pr2 * cur2) / (pr1 * cur1)
    rt = (x - 1)

    return [f'{(pr2 * (1 + pr_mult)).round(1)}$',
            str(((((1 + pr_mult) * (1 + cur_mult) * rt + (1 + pr_mult) * (1 + cur_mult) - 1) * (tax if (1 + pr_mult) * (1 + cur_mult) * x > 1 else 1)) * 100).round(1)) + '%',
            str(((((1 + pr_mult) * rt + (1 + pr_mult) - 1) * (tax if (1 + pr_mult) * x > 1 else 1)) * 100).round(1)) + '%',
            str(((((1 + pr_mult) * (1 - cur_mult) * rt + (1 + pr_mult) * (1 - cur_mult) - 1) * (tax if (1 + pr_mult) * (1 - cur_mult) * x > 1 else 1)) * 100).round(1)) + '%',

            f'{pr2.round(1)}$',
            str(((((1 + cur_mult) * rt + (1 + cur_mult) - 1) * (tax if (1 + cur_mult) * x > 1 else 1)) * 100).round(1)) + '%',
            str(((rt * 100) * (tax if x > 1 else 1)).round(1)) + '%',
            str(((((1 - cur_mult) * rt + (1 - cur_mult) - 1) * (tax if (1 - cur_mult) * x > 1 else 1)) * 100).round(1)) + '%',

            f'{(pr2 * (1 - pr_mult)).round(1)}$',
            str(((((1 - pr_mult) * (1 + cur_mult) * rt + (1 - pr_mult) * (1 + cur_mult) - 1) * (tax if (1 - pr_mult) * (1 + cur_mult) * x > 1 else 1)) * 100).round(1)) + '%',
            str(((((1 - pr_mult) * rt + (1 - pr_mult) - 1) * (tax if (1 - pr_mult) * x > 1 else 1)) * 100).round(1)) + '%',
            str(((((1 - pr_mult) * (1 - cur_mult) * rt + (1 - pr_mult) * (1 - cur_mult) - 1) * (tax if (1 - pr_mult) * (1 - cur_mult) * x > 1 else 1)) * 100).round(1)) + '%']


def matrix_label(ticker, cur):
    cur_mult = 0.03
    return [str(ticker), str(((1 + cur_mult) * cur).round(1)) + 'P', str(cur.round(1)) + 'P', str(((1 - cur_mult) * cur).round(1)) + 'P']


def return_usd_rub(tickers, start_date):

    if not tickers:
        tickers = ['AAPL']


    tickers.append('USDRUB')
    prices_data = pd.DataFrame()
    for ticker in tickers:
        pr = fmp_prices(ticker, pd.to_datetime(start_date[0].strftime('%Y-%m-%d')))
        if pr is None:
            continue
        prices_data = prices_data.append(pr)
    prices_data['date'] = pd.to_datetime(prices_data['date'])
    prices_data = pd.pivot_table(prices_data, values='adj_close_price', index='date', columns='ticker')
    prices_data = prices_data.resample('D').ffill().ffill()
    prices_data = prices_data.dropna(axis=0)

    returns_usd = pd.DataFrame()
    returns_rub = pd.DataFrame()

    data_table = pd.DataFrame()
    matrices = []
    matrix_labels = []

    # доходность
    for i, ticker in enumerate(tickers):
        if ticker == 'USDRUB':
            continue

        data_table.loc[i, 'ticker'] = ticker

        try:
            data_table.loc[i, 'start_date'] = start_date[tickers.index(ticker)].strftime("%d.%m.%Y")
        except AttributeError:
            data_table.loc[i, 'start_date'] = start_date[tickers.index(ticker)]

        quotes = prices_data.loc[start_date[0]:, :]
        try:
            price_usd = quotes[ticker]
            price_rub = quotes[ticker] * quotes['USDRUB']
        except KeyError:
            data_table.loc[i, 'return USD'] = None
            data_table.loc[i, 'return RUB'] = None
            data_table.loc[i, 'tax USD, %'] = None
            returns_usd.loc[start_date[0], ticker] = 0
            returns_rub.loc[start_date[0], ticker] = 0
            continue

        # рекомендация получена по цене входа, доходности в абсолютном выражении и с учетом курсовой разницы
        # data_table.loc[i, 'recommendation'] = recommendation(price_rub.values[-1]/quotes['USDRUB'][0],
        # price_usd.values[-1], price_usd.values[0])

        last_pr = quotes[ticker].values[-1]
        last_cur = quotes['USDRUB'].values[-1]
        first_pr = quotes[ticker].values[0]
        first_cur = quotes['USDRUB'].values[0]
        data_table.loc[i, 'last_price'] = str(round(last_pr, 1)) + ' $'
        data_table.loc[i, 'last_rub'] = str(round(last_cur, 1)) + ' P'

        price_usd = price_usd.apply(lambda x: x - price_usd[0])
        price_rub = price_rub.apply(lambda x: (x - price_rub[0]) / first_cur)
        price_rub.name = ticker

        # доходность в процентах
        data_table.loc[i, 'return USD'] = str((price_usd.values[-1]/first_pr * 100).round(1)) + ' %'
        data_table.loc[i, 'return RUB'] = str((price_rub.values[-1]/first_pr * 100).round(1)) + ' %'

        # налог в абсолютном выражении и фактический с учетом курсовой разницы data_table.loc[i, 'tax USD'] = str(
        # round(max(price_rub.values[-1] * 0.13 * q, 0.0), 2)) + ' $' data_table.loc[i, 'tax RUB'] = str(round(max(
        # price_rub.values[-1] * 0.13 * quotes['USDRUB'][0] * q, 0.0), 2)) + ' ₽'

        data_table.loc[i, 'tax USD, %'] = str(round(price_rub.values[-1] * (0.87 if price_rub.values[-1] > 0 else 1)/first_pr * 100, 1)) + ' %'

        matrix = matrix_data(last_pr, last_cur, first_pr, first_cur)
        m_label = matrix_label(ticker, last_cur)
        matrices.extend(matrix)
        matrix_labels.extend(m_label)
        returns_usd = returns_usd.merge(price_usd, left_index=True, right_index=True, how='outer')
        returns_rub = returns_rub.merge(price_rub, left_index=True, right_index=True, how='outer')

    # общая доходность портфеля
    res_usd = return_portfolio(returns_usd, [1])
    res_rub = return_portfolio(returns_rub, [1])
    res = {'return_usd': res_usd.values, 'return_rub': res_rub.values,
           'date': res_usd.index.to_list()}
    res = ([dict(zip(res, t)) for t in zip(*res.values())])

    data_table = list(data_table.itertuples(index=False, name=None))

    matrix_labels.extend(matrices)
    space_header_1 = max([len(x) for x in [matrix_labels[1], matrix_labels[2], matrix_labels[3], matrix_labels[6], matrix_labels[15]]])
    space_header_2 = max([len(x) for x in matrix_labels[::4]])
    string_table = f"""<pre>
    {matrix_labels[0]}{''.join(' ' for x in range(len(matrix_labels[0]), space_header_2))}┆{matrix_labels[1]}{''.join(' ' for x in range(len(matrix_labels[1]), space_header_1))} {matrix_labels[2]}{''.join(' ' for x in range(len(matrix_labels[2]), space_header_1))} {matrix_labels[3]}{''.join(' ' for x in range(len(matrix_labels[3]), space_header_1))}
    {''.join('-' for x in range(0, space_header_2))}┆{''.join('-' for x in range(0, sum([len(x) for x in matrix_labels[1:4]]) + 2))}
    {matrix_labels[4]}{''.join(' ' for x in range(len(matrix_labels[4]), space_header_2))}┆{matrix_labels[5]}{''.join(' ' for x in range(len(matrix_labels[5]), space_header_1))} {matrix_labels[6]}{''.join(' ' for x in range(len(matrix_labels[6]), space_header_1))} {matrix_labels[7]}{''.join(' ' for x in range(len(matrix_labels[7]), space_header_1))}
    {matrix_labels[8]}{''.join(' ' for x in range(len(matrix_labels[8]), space_header_2))}┆{matrix_labels[9]}{''.join(' ' for x in range(len(matrix_labels[9]), space_header_1))} {matrix_labels[10]}{''.join(' ' for x in range(len(matrix_labels[10]), space_header_1))} {matrix_labels[11]}{''.join(' ' for x in range(len(matrix_labels[11]), space_header_1))}
    {matrix_labels[12]}{''.join(' ' for x in range(len(matrix_labels[12]), space_header_2))}┆{matrix_labels[13]}{''.join(' ' for x in range(len(matrix_labels[13]), space_header_1))} {matrix_labels[14]}{''.join(' ' for x in range(len(matrix_labels[14]), space_header_1))} {matrix_labels[15]}{''.join(' ' for x in range(len(matrix_labels[15]), space_header_1))}
    </pre>"""
    return data_table[0], string_table, matrix_labels[1], matrix_labels[8], matrix_labels[9]


