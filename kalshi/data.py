from sys import argv
from kalshi import *

# # get series
# response = get('https://external-api.kalshi.com/trade-api/v2/series?category=Sports&tags=Boxing')
# data = response.json()
# for series in data['series']:
#     # if 'Major League Soccer' in series['title']:
#     print(series['ticker'] + '\t\t' + series['title'])
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
    }
}

if len(argv) == 1:
    print(f'usage: python3 {argv[0]} league')
    exit(1)

league = LEAGUES[argv[1]]
events = get_historical_events(league['series_ticker'], n=1000, outcomes=league['outcomes'])

print('P(A)	P(B)	A	B')

for event in events:
    cooldown = 0
    moneyline = None

    while not moneyline:
        if cooldown == 0:
            cooldown = 1
        else:
            time.sleep(cooldown)
            cooldown *= 2

        moneyline = get_historical_moneyline(event['markets'], n=6, interval_minutes=60)

    if any(prices[-1]['yes_ask'] == 1 for prices in moneyline.values()) and not any(prices[0]['yes_ask'] == 1 or prices[0]['yes_ask'] == 0 for prices in moneyline.values()):
        for index in [0, -1]:
            for market in event['markets']:
                print(moneyline[market['ticker']][index]['yes_ask'], end='\t')

        print()
