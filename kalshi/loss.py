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
for i, row in enumerate(data[:30]):
    print(row[0])
    loss = compute_loss(row[2:5], row[5:])
    losses.append(loss)

print(f'Outcome: {mean(losses):.4f} log loss')

# 0.817 log loss is the number to beat!
