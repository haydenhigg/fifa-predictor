from pathlib import Path
from typing import Any
import csv
from monte_carlo import MonteCarlo, Function
from random import gauss
import numpy as np
from scipy.stats import nbinom, poisson
# from sklearn.neural_network import MLPClassifier
import math
from sys import argv

INPUT_PATH = Path('ha_fifa_matches.csv')

TEST_FRACTION = 0.08
STR_LATENT_LR = 0.09
HOME_LATENT_LR = 0.0
CORR_LATENT_LR = 0.16

def read_matches() -> list[dict[str, Any]]:
    matches = []

    with INPUT_PATH.open() as f:
        for row in csv.reader(f):
            matches.append({
                'date': row[0],
                'status': row[1],
                'teams': [row[2], row[5]],
                'goals': [int(row[3]), int(row[6])],
                'homes': [int(row[4]), int(row[7])]
            })

    return matches

def model(a_latent: dict, b_latent: dict, a_home: int, b_home: int) -> float:
    a_logit = a_latent['offense'] - b_latent['defense'] + a_latent['home'] * a_home
    b_logit = b_latent['offense'] - a_latent['defense'] + b_latent['home'] * b_home

    return math.exp(a_logit + a_latent['correlation'] * b_logit)

def encode_outcome(a: int, b: int) -> list[float]:
    outcome = [0] * 3
    if a > b:
        outcome[0] = 1
    elif b > a:
        outcome[2] = 1
    else:
        outcome[1] = 1

    return outcome

def compute_loss(ps: list[float], target: list[float]) -> float:
    loss = 0

    for i, p in enumerate(ps):
        loss -= target[i] * math.log(min(max(p, 1e-15), 1-1e-15))

    return loss

def predict_outcome_poisson(lam0: float, lam1: float) -> list[float]:
    outcome = [0] * 3

    for g0 in range(20):
        p0 = poisson.pmf(g0, lam0)

        for g1 in range(20):
            p = p0 * poisson.pmf(g1, lam1)

            if g0 > g1:
                outcome[0] += p
            elif g1 > g0:
                outcome[2] += p
            else:
                outcome[1] += p

    p_sum = sum(outcome)

    return [p / p_sum for p in outcome]

def softmax(zs: list[float], t: float = 1.0) -> list[float]:
    ezs = [math.exp(z / t) for z in zs]
    sum_ezs = sum(ezs)

    return [ez / sum_ezs for ez in ezs]

# print('Date\tTeam A\tTeam B\tOff A\tDef A\tCorr A\txG A\tOff B\tDef B\tCorr B\txG B\tP(A)\tP(Tie)\tP(B)\tA\tTie\tB\tResidual')

if __name__ == '__main__':
    matches = read_matches()
    num_matches = len(matches)
    num_test_matches = int(float(num_matches) * TEST_FRACTION)

    latents = {}

    log_loss = 0
    mse = 0
    accuracy = 0

    # xs_train, xs_test = [], []
    # ys_train, ys_test = [], []

    for i, match in enumerate(matches[::-1]):
        # ensure teams have latents
        for team in match['teams']:
            if team not in latents:
                latents[team] = {
                    'offense': 0,
                    'defense': 0,
                    'correlation': 0,
                    'home': 0,
                }

        # calculate expected goals from latents
        expected_goals = []
        for j in range(len(match['teams'])):
            a = match['teams'][j]
            b = match['teams'][(j + 1) % 2]

            expected_goals.append(model(latents[a], latents[b], match['homes'][j], match['homes'][(j + 1) % 2]))

        # make prediction and record
        # a_latent = latents[match['teams'][0]]
        # b_latent = latents[match['teams'][1]]
        # x = predict_outcome_poisson(*expected_goals) + [
        #     a_latent['offense'],
        #     a_latent['defense'],
        #     a_latent['correlation'],
        #     a_latent['home'],
        #     b_latent['offense'],
        #     b_latent['defense'],
        #     b_latent['correlation'],
        #     b_latent['home'],
        # ]
        y = encode_outcome(*match['goals'])

        if i >= num_matches - num_test_matches:
            print(match['date'], match['teams'])
            prediction = predict_outcome_poisson(*expected_goals)
            min_i, max_i = 0, 0
            for i, p in enumerate(prediction):
                if p > prediction[max_i]:
                    max_i = i
                elif p < prediction[min_i]:
                    min_i = i

            # x = min(expected_goals) / max(expected_goals)
            # s = 1/(1-math.log(x))
            # prediction = softmax([math.log(p) for p in prediction], 0.7)
            prediction[max_i] = 0.98
            prediction[(max_i + 1) % 3] = 0.01
            prediction[(max_i + 2) % 3] = 0.01

            if max_i == y.index(max(y)):
                accuracy += 1

            # prediction[max_i] *= 1.4
            # prediction[min_i] *= 0.6
            # prediction = [p / sum(prediction) for p in prediction]

            log_loss += compute_loss(prediction, y)
            mse += ((expected_goals[0] - expected_goals[1]) - (match['goals'][0] - match['goals'][1])) ** 2

            # calculate residual
            a = match['teams'][0]
            b = match['teams'][1]
            # r = -math.log(prediction[y.index(max(y))])
            # print(f'{match["date"]}\t{a}\t{b}\t{latents[a]["offense"]:.4f}\t{latents[a]["defense"]:.4f}\t{latents[a]["correlation"]:.4f}\t{model(latents[a], latents[b], 0, 0):.4f}\t{latents[b]["offense"]:.4f}\t{latents[b]["defense"]:.4f}\t{latents[b]["correlation"]:.4f}\t{model(latents[b], latents[a], 0, 0):.4f}\t{prediction[0]:.4f}\t{prediction[1]:.4f}\t{prediction[2]:.4f}\t{y[0]:.4f}\t{y[1]:.4f}\t{y[2]:.4f}\t{r:.4f}')

        #     xs_test.append(x)
        #     ys_test.append(y)
        # else:
        #     xs_train.append(x)
        #     ys_train.append(y)

        # update latents
        for j in range(len(match['teams'])):
            a = match['teams'][j]
            b = match['teams'][(j + 1) % 2]

            gradient = match['goals'][j] - expected_goals[j]

            latents[a]['correlation'] += gradient * (latents[b]['offense'] - latents[a]['defense'] + latents[b]['home'] * match['homes'][(j + 1) % 2]) * CORR_LATENT_LR

        for j in range(len(match['teams'])):
            a = match['teams'][j]
            b = match['teams'][(j + 1) % 2]

            gradient = match['goals'][j] - expected_goals[j]

            latents[a]['offense'] += gradient * STR_LATENT_LR
            latents[b]['defense'] -= gradient * STR_LATENT_LR

            latents[a]['home'] += gradient * match['homes'][j] * HOME_LATENT_LR

    log_loss /= num_test_matches
    mse /= num_test_matches
    accuracy /= num_test_matches

    print(f'Outcome: {log_loss:.3f} log loss')
    print(f'Outcome: {100 * accuracy:.1f}% accuracy')
    print(f'Goal difference: {math.sqrt(mse):.3f} RMSE')

    # nn = MLPClassifier(hidden_layer_sizes=[80], max_iter=300)
    # nn.fit(xs_train, ys_train)

    # log_loss = 0

    # for i, x in enumerate(xs_test):
    #     prediction = nn.predict_proba([x])
    #     log_loss += compute_loss(prediction[0], ys_test[i])

    # log_loss /= num_test_matches

    # print(f'Neural network outcome: {log_loss:.3f} log loss')

    if len(argv) == 1:
        exit(0)

    a, b = argv[1], argv[2]
    expected_goals = [model(latents[a], latents[b], 0, 0), model(latents[b], latents[a], 0, 0)]

    prediction = predict_outcome_poisson(*expected_goals)
    min_i, max_i = 0, 0
    for i, p in enumerate(prediction):
        if p > prediction[max_i]:
            max_i = i
        elif p < prediction[min_i]:
            min_i = i
    prediction[max_i] *= 1.4
    prediction[min_i] *= 0.6
    prediction[1] *= 1.4

    print([p / sum(prediction) for p in prediction])
