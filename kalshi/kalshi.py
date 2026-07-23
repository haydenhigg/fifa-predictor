import time
from httpx import get
from datetime import datetime

EVENTS_URL = 'https://external-api.kalshi.com/trade-api/v2/events'
CANDLESTICKS_URL = 'https://external-api.kalshi.com/trade-api/v2/markets/candlesticks'
HISTORICAL_MARKETS_URL = 'https://external-api.kalshi.com/trade-api/v2/historical/markets'
HISTORICAL_CANDLESTICKS_URL_FMT = 'https://external-api.kalshi.com/trade-api/v2/historical/markets/{}/candlesticks'

# get live data
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
    events = []

    while not events or (n >= 0 and len(events) < n and params['cursor']):
        response = get(EVENTS_URL, params=params)
        data = response.json()

        events.extend(data['events'])

        if data['cursor'] and data['cursor'] != '':
            params['cursor'] = data['cursor']
        else:
            break

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
    response = get(CANDLESTICKS_URL, params={
        'market_tickers': ','.join(market_tickers),
        'start_ts': start_ts,
        'end_ts': then,
        'period_interval': interval_minutes
    })
    data = response.json()

    # pare down response
    moneyline = {}

    if 'markets' not in data:
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

# get historical data
def get_historical_events(series_ticker: str, n: int = -1, outcomes: int = 2) -> list[dict]:
    # make params
    params = {'series_ticker': series_ticker}

    if n >= 0:
        params['limit'] = min(n * outcomes, 1000)

    # fetch markets and merge per event
    keyed_events = {}

    while not keyed_events or (n >= 0 and len(keyed_events) < n and params['cursor']):
        response = get(HISTORICAL_MARKETS_URL, params=params)
        data = response.json()

        for market in data['markets']:
            if market['event_ticker'] in keyed_events:
                keyed_events[market['event_ticker']]['markets'].append(market)
            else:
                keyed_events[market['event_ticker']] = {
                    'series_ticker': series_ticker,
                    'event_ticker': market['event_ticker'],
                    'markets': [market]
                }

        if data['cursor'] and data['cursor'] != '':
            params['cursor'] = data['cursor']
        else:
            break

    events = list(keyed_events.values())

    # TODO: make sure the last event isn't missing any markets

    return events

def get_historical_moneyline(markets: list, n: int = -1, interval_minutes: int = 1440) -> dict:
    moneyline = {}

    for market in markets:
        event_time_iso_timestamp = market['occurrence_datetime']
        event_time = int(datetime.fromisoformat(event_time_iso_timestamp).timestamp())

        start_ts = event_time - 60 * interval_minutes * int(min(max(n, 1), 20_160 / interval_minutes, 5000))

        # fetch candlesticks
        response = get(HISTORICAL_CANDLESTICKS_URL_FMT.format(market['ticker']), params={
            'start_ts': start_ts,
            'end_ts': event_time - 60 * interval_minutes,
            'period_interval': interval_minutes
        })
        data = response.json()

        # pare down response
        prices = []

        for candlestick in data.get('candlesticks', []):
            prices.append({
                'end_period_ts': int(candlestick['end_period_ts']),
                'yes_ask': float(candlestick['yes_ask']['close'])
            })

        prices.append({
            'end_period_ts': event_time,
            'yes_ask': float(market.get('settlement_value_dollars', market['yes_ask_dollars']))
        })

        moneyline[market['ticker']] = prices

    return moneyline
