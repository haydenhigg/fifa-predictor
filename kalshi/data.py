from sys import argv
from kalshi import *

# # get series
# response = get('https://external-api.kalshi.com/trade-api/v2/series?category=Sports&tags=Tennis')
# data = response.json()
# for series in data['series']:
#     if 'WTA' in series['title']:
#         print(series['ticker'] + '\t\t' + series['title'])
# exit()

LEAGUES = {
    'atp': {
        'series_ticker': 'KXATPMATCH',
        'outcomes': 2
    },
    'atpchallenger': {
        'series_ticker': 'KXATPCHALLENGERMATCH',
        'outcomes': 2
    },
    'mlb': {
        'series_ticker': 'KXMLBGAME',
        'outcomes': 2
    },
    'mls': {
        'series_ticker': 'KXMLSGAME',
        'outcomes': 3
    },
    'boxing': {
        'series_ticker': 'KXBOXING',
        'outcomes': 2
    },
    'ligamx': {
        'series_ticker': 'KXLIGAMXGAME',
        'outcomes': 3
    },
    'wta': {
        'series_ticker': 'KXWTAMATCH',
        'outcomes': 2
    }
}

if len(argv) == 1:
    print(f'usage: python3 {argv[0]} league')
    exit(1)

league = LEAGUES[argv[1]]
# events = get_historical_events(league['series_ticker'], n=1000, outcomes=league['outcomes'])
events = get_events(league['series_ticker'], n=1000)

print('P(A)	P(B)	A	B')

for event in events:
    if 'markets' not in event:
        continue

    cooldown = 0
    moneyline = None

    while not moneyline:
        if cooldown == 0:
            cooldown = 1
        elif cooldown > 30:
            print('time out')
            exit()
        else:
            time.sleep(cooldown)
            cooldown *= 2

        # moneyline = get_historical_moneyline(event['markets'], n=6, interval_minutes=60)
        moneyline = get_moneyline(event['markets'], n=6, interval_minutes=60)

    if any(prices[-1]['yes_ask'] == 1 for prices in moneyline.values()):
        for index in [0, -1]:
            for market in event['markets']:
                print('{:.02f}'.format(moneyline[market['ticker']][index]['yes_ask']), end='\t')

        print()
