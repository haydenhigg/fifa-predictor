from pathlib import Path
from typing import Any
import csv
from monte_carlo import MonteCarlo
import numpy as np
from scipy.stats import nbinom, poisson
# from sklearn.neural_net import MLPClassifier
import math
from sys import argv

INPUT_PATH = Path('ha_fifa_matches.csv')

TEST_FRACTION = 0.2

LATENT_LR = 0.07

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
                # 'tournament': row[8],
                # 'tournament_stage': row[9],
                # 'stadium': row[10],
            })

    return matches

def model(a_latent: dict, b_latent: dict, a_home: int, b_home: int) -> float:
    b_diff = b_latent['offense'] - a_latent['defense']

    return math.exp(a_latent['offense'] - b_latent['defense'] + a_latent['home'] * a_home + a_latent['correlation'] * b_diff)

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

    for g0 in range(12):
        p0 = poisson.pmf(g0, lam0)

        for g1 in range(12):
            p = p0 * poisson.pmf(g1, lam1)

            if g0 > g1:
                outcome[0] += p
            elif g1 > g0:
                outcome[2] += p
            else:
                outcome[1] += p

    p_sum = sum(outcome)

    return [p / p_sum for p in outcome]

if __name__ == '__main__':
    matches = read_matches()
    num_matches = len(matches)
    num_test_matches = int(float(num_matches) * TEST_FRACTION)

    latents = {}

    log_loss = 0
    mse = 0

    for i, match in enumerate(matches[::-1]):
        # ensure teams have latents
        for team in match['teams']:
            if team not in latents:
                latents[team] = {
                    'offense': 0,
                    'defense': 0,
                    'correlation': 0,
                    'home': 0
                }

        # calculate expected goals from latents
        expected_goals = []
        for j in range(len(match['teams'])):
            a = match['teams'][j]
            b = match['teams'][(j + 1) % 2]

            expected_goals.append(model(latents[a], latents[b], match['homes'][j], match['homes'][(j + 1) % 2]))

        # make prediction and record
        if i >= num_matches - num_test_matches:
            prediction = predict_outcome_poisson(*expected_goals)
            outcome = encode_outcome(*match['goals'])

            log_loss += compute_loss(prediction, outcome)
            mse += ((expected_goals[0] - expected_goals[1]) - (match['goals'][0] - match['goals'][1])) ** 2

        # update latents
        for j in range(len(match['teams'])):
            a = match['teams'][j]
            b = match['teams'][(j + 1) % 2]

            gradient = match['goals'][j] - expected_goals[j]

            latents[a]['offense'] += gradient * LATENT_LR
            latents[b]['defense'] -= gradient * LATENT_LR

            latents[a]['correlation'] += gradient * (latents[b]['offense'] - latents[a]['defense']) * LATENT_LR
            latents[a]['home'] += gradient * match['homes'][j] * LATENT_LR

    log_loss /= num_test_matches
    mse /= num_test_matches

    print(f'Outcome: {log_loss:.3f} log loss')
    print(f'Goal difference: {math.sqrt(mse):.3f} RMSE')

    if len(argv) == 1:
        exit(0)

    a, b = argv[1], argv[2]
    expected_goals = [model(latents[a], latents[b]), model(latents[b], latents[a])]

    print(predict_outcome_poisson(*expected_goals))
