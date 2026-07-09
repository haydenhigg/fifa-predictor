import time
from httpx import get
from datetime import datetime

# # get series
# response = get('https://external-api.kalshi.com/trade-api/v2/series?category=Sports&tags=Soccer')
# data = response.json()

# for series in data['series']:
#     if 'World Cup Game' in series['title']:
#         print(series['ticker'] + '\t' + series['title'])
# exit()

SERIES_TICKER = 'KXWCGAME' # World Cup Game

# get event moneylines
def get_events(series_ticker: str, n: int = -1, future_only: bool = False) -> list[dict]:
    # make params
    params = {
        'series_ticker': series_ticker,
        'with_nested_markets': True
    }

    if n >= 0:
        params['limit'] = min(n, 200)

    if future_only:
        params['min_close_ts'] = int(time.time())

    # fetch events
    EVENTS_API_URL = 'https://external-api.kalshi.com/trade-api/v2/events'
    events = []

    while not events or (n >= 0 and len(events) < n and params['cursor']):
        response = get(EVENTS_API_URL, params=params)
        data = response.json()

        events.extend(data['events'])

        if data['cursor'] and data['cursor'] != '':
            params['cursor'] = data['cursor']

    return events

def get_moneyline(markets: list, n: int = -1, interval_minutes: int = 1440) -> dict:
    # get current moneyline
    now = int(time.time())
    then = now

    current_moneyline = {}
    all_unstarted = True

    for market in markets:
        current_moneyline[market['ticker']] = [{
            'end_period_ts': now,
            'yes_ask': float(market.get('settlement_value_dollars', market['yes_ask_dollars']))
        }]

        if 'occurrence_datetime' not in market:
            continue

        event_time_iso_timestamp = market['occurrence_datetime']
        event_time = int(datetime.fromisoformat(event_time_iso_timestamp).timestamp())

        if event_time < now:
            if event_time < then:
                then = event_time

            all_unstarted = False

    if n == 1 and all_unstarted:
        return current_moneyline

    # make params
    market_tickers = [market['ticker'] for market in markets]
    start_ts = then - 60 * interval_minutes * int(min(max(n, 1), 20_160 / interval_minutes, 5000))

    # fetch candlesticks for historical moneylines
    CANDLESTICKS_API_URL = 'https://external-api.kalshi.com/trade-api/v2/markets/candlesticks'
    response = get(CANDLESTICKS_API_URL, params={
        'market_tickers': ','.join(market_tickers),
        'start_ts': start_ts,
        'end_ts': then,
        'period_interval': interval_minutes
    })
    data = response.json()

    # pare down response
    moneyline = {}

    if 'markets' not in data:
        print(data)
        return moneyline

    for market in data['markets']:
        prices = []

        for candlestick in market['candlesticks']:
            prices.append({
                'end_period_ts': int(candlestick['end_period_ts']),
                'yes_ask': float(candlestick['yes_ask']['close_dollars'])
            })

        prices.extend(current_moneyline[market['market_ticker']])

        moneyline[market['market_ticker']] = prices

    return moneyline

events = get_events(SERIES_TICKER)

print('event_name        	event_ticker          	P(A)	P(B)	P(Tie)	A	B	Tie')

for event in events:
    cooldown = 0
    moneyline = None

    while not moneyline:
        if cooldown == 0:
            cooldown = 1
        else:
            time.sleep(cooldown)
            cooldown *= 2

        moneyline = get_moneyline(event['markets'], n=(24*14), interval_minutes=60)

    # print(event['sub_title'])
    # for market_ticker, prices in moneyline.items():
    #     print(market_ticker, ','.join([str(price['yes_ask']) for price in prices]))

    code = event['event_ticker'][-6:]

    print('\t'.join([
        event['sub_title'],
        event['event_ticker'],
        str(moneyline[event['event_ticker'] + '-' + code[:3]][0]['yes_ask']),
        str(moneyline[event['event_ticker'] + '-' + code[3:]][0]['yes_ask']),
        str(moneyline[event['event_ticker'] + '-TIE'][0]['yes_ask']),
        str(moneyline[event['event_ticker'] + '-' + code[:3]][-1]['yes_ask']),
        str(moneyline[event['event_ticker'] + '-' + code[3:]][-1]['yes_ask']),
        str(moneyline[event['event_ticker'] + '-TIE'][-1]['yes_ask'])
    ]))
