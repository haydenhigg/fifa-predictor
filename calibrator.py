from math import log

with open('data.tsv') as f:
    data = [[float(x) for x in row.split('\t')[3:]] for row in f.read().strip().split('\n')[1:]]

train = 65

X = []
y = []

for row in data[:train]:
    X.append(row[:8] + [log(row[8]), log(row[9]), log(row[10])])

    # # calibration regressor
    # y.append([o - p for o, p in zip(row[11:14], row[8:11])])

    # classifier
    y.append(row[11:14])

from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from math import log
from statistics import mean

# mlp = MLPRegressor(hidden_layer_sizes=(5,), max_iter=10_000, random_state=1)
# mlp.fit(X, y)
# mlp = LinearRegression()
# mlp.fit(X, y)
mlp = MLPClassifier(hidden_layer_sizes=(50,50), max_iter=10_000, random_state=1)
mlp.fit(X, y)
# mlp = OneVsRestClassifier(LogisticRegression())
# mlp.fit(X, y)

sse = 0
losses = []

# # calibration regressor
# def normalize(xs: list[float]) -> list[float]:
#     clamped_xs = [min(max(x, 0), 1) for x in xs]
#     total = sum(clamped_xs)

#     return [cx / total for cx in clamped_xs]

def compute_loss(ps: list[float], target: list[float]) -> float:
    loss = 0

    for i, p in enumerate(ps):
        loss -= float(target[i]) * log(min(max(float(p), 1e-15), 1-1e-15))

    return loss

for row in data[train:]:
    # # calibration regressor
    # ps = row[8:11]
    # cs = mlp.predict([row[:8]])[0]

    # y_hat = normalize([p + c for p, c in zip(ps, cs)])

    # classifier
    y_hat = mlp.predict([row[:11]])[0]

    print(y_hat, row[11:14])
    losses.append(compute_loss(y_hat, row[11:14]))

    for i, o in enumerate(row[11:14]):
        d = o - y_hat[i]
        sse += d * d

print('MSE:', sse / (len(data[train:]) * 3))
print(f'Outcome: {mean(losses):.4f} log loss')
