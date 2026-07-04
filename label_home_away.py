import json

with open('fifa_matches.csv') as f:
    data = [row.split(',') for row in f.read().strip().split('\n')]

with open('locations.json') as f:
    locations = json.load(f)

labeled_data = []

for row in data:
    location = row[8]
    if location not in locations:
        locations[location] = input(f'Home for {location}? [{row[2]}/{row[4]}] ')

    labeled_data.append([
        row[0],
        row[1],
        row[2],
        row[3],
        '1' if row[2] == locations[location] else '0',
        row[4],
        row[5],
        '1' if row[4] == locations[location] else '0',
        row[6],
        row[7],
        row[8]
    ])

with open('locations.json', 'w') as f:
    json.dump(locations, f)

with open('ha_fifa_matches.csv', 'w') as f:
    f.write('\n'.join([','.join(row) for row in labeled_data]))
