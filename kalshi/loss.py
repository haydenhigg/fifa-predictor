import math
from statistics import mean

def compute_loss(ps: list[float], target: list[float]) -> float:
    loss = 0

    for i, p in enumerate(ps):
        loss -= float(target[i]) * math.log(min(max(float(p), 1e-15), 1-1e-15))

    return loss

with open('data.tsv') as f:
    data = [row.split('\t') for row in f.read().strip().split('\n')[1:]]

losses = []
for i, row in enumerate(data):
    loss = compute_loss(row[2:5], row[5:])
    losses.append(loss)

    if loss > 1.5:
        print(i + 1, row, loss)

print(f'Outcome: {mean(losses):.3f} log loss')
