from sys import argv
from statistics import quantiles
from math import log#, ceil

if len(argv) == 1:
    print(f'usage: python3 {argv[0]} file.tsv')
    exit(1)

FILE = argv[1]
OUTCOMES = 2
BINS = 6

with open(FILE) as f:
    data = [[float(x) for x in row.split('\t')] for row in f.read().strip().split('\n')[1:]]

pred_outcomes = [row[:OUTCOMES].index(max(row[:OUTCOMES])) for row in data]
outcomes = [row[OUTCOMES:].index(max(row[OUTCOMES:])) for row in data]

def compute_ev(min_p: float = 0, max_p: float = 1) -> tuple[int, float, float, float]:
    n = 0

    p_sum = 0
    wins = 0
    value = 0

    for i, row in enumerate(data):
        p = row[pred_outcomes[i]]
        if p <= min_p or p > max_p: # half-open interval (min_p, max_p]
            continue

        n += 1
        p_sum += p

        if pred_outcomes[i] == outcomes[i]:
            wins += 1
            value += 1 / p

    if n == 0:
        return 0, 0, 0, 0

    return n, p_sum / n, wins / n, value / n - 1

pred_outcome_probs = [row[pred_outcomes[i]] for i, row in enumerate(data)]
bins = quantiles(pred_outcome_probs, n=BINS)

print('bin\t\t#\tavg. cost\twin rate\tEV')

for i in range(BINS):
    low = 1 / OUTCOMES if i == 0 else bins[i - 1]
    high = 1 if i == BINS - 1 else bins[i]

    n, avg_cost, win_rate, ev = compute_ev(low, high)

    # kl_divergence = win_rate * log(win_rate / avg_cost) + (1 - win_rate) * log((1 - win_rate) / (1 - avg_cost))

    print(f'{low:.02f}-{high:.02f}\t{n}\t{avg_cost:.3f}\t\t{win_rate * 100:.1f}%\t\t{ev * 100:+.1f}%')
