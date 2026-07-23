from sys import argv
from statistics import quantiles, mean

if len(argv) == 1:
    print(f'usage: python3 {argv[0]} file.tsv [number_of_bins]')
    exit(1)

FILE = argv[1]
BINS = int(argv[2] if len(argv) >= 3 else 10)

def get_bins(ps: list[float], n: int) -> list[float]:
    return [0] + quantiles(ps, n=n, method='inclusive') + [1]

def bin_for_p(bins: list[float], p: float) -> int:
    i = 0
    while i < len(bins) and p > bins[i]:
        i += 1

    return i - 1

with open(FILE) as f:
    data = [[float(x) for x in row.strip().split('\t')] for row in f.read().strip().split('\n')[1:]]
    outcomes = int(len(data[0]) / 2)

bins = get_bins([p for row in data for p in row[:2]], BINS)

ps = {}
factors = {}

for row in data:
    for i in range(outcomes):
        p = row[i]
        outcome = row[i + outcomes]

        bin = bin_for_p(bins, p)
        factor = 1 / p if outcome == 1 else 0

        if bin in ps:
            ps[bin].append(p)
            factors[bin].append(factor)
        else:
            ps[bin] = [p]
            factors[bin] = [factor]

print('bin\t\t#\tmean\twin%\tROI')
FMT = '{:.02f}-{:.02f}\t{}\t{:.03f}\t{:.1f}%\t{:+.1f}%'

for i in sorted(factors.keys()):
    count = len(factors[i])
    win_count = len([factor for factor in factors[i] if factor > 0])

    print(FMT.format(
        bins[i] + 0.01,
        bins[i + 1],
        count,
        mean(ps[i]),
        (win_count / count) * 100,
        (mean(factors[i]) - 1) * 100
    ))
