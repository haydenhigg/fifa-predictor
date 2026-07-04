package main

import (
	"encoding/csv"
	"fmt"
	"github.com/haydenhigg/lynn"
	"io"
	"math"
	"os"
	"slices"
	"strconv"
	"time"
)

const INPUT_PATH = "fifa_matches.csv"

const LATENT_STRENGTH_LEARNING_RATE = 0.24
const LATENT_OPENNESS_LEARNING_RATE = 0.12
const LATENT_POINTS_LEARNING_RATE = 0.12

const MODEL_LEARNING_RATE = 0.01
const TEST_FRACTION = 0.1
const KELLY_MULTIPLIER = 0.25

type Match struct {
	Date       time.Time
	Status     string
	Tournament string
	Teams      []string
	Scores     []int
	Outcome    []float64
}

func readMatches(fileName string) ([]Match, error) {
	file, err := os.Open(fileName)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	matches := []Match{}
	reader := csv.NewReader(file)
	for {
		record, err := reader.Read()
		if err == io.EOF {
			break
		} else if err != nil {
			return nil, err
		}

		date, _ := time.Parse("02 Jan 2006", record[0])
		homeScore, _ := strconv.Atoi(record[3])
		awayScore, _ := strconv.Atoi(record[5])

		outcome := make([]float64, 3)
		if homeScore > awayScore {
			outcome[0] = 1
		} else if awayScore > homeScore {
			outcome[2] = 1
		} else {
			outcome[1] = 1
		}

		matches = append(matches, Match{
			Date:       date,
			Status:     record[1],
			Tournament: record[6],
			Teams:      []string{record[2], record[4]},
			Scores:     []int{homeScore, awayScore},
			Outcome:    outcome,
		})
	}

	return matches, nil
}

type Latent struct {
	Strength, Offense, Defense, Openness float64
}

func makeXs(latents map[string]*Latent, teams []string) []float64 {
	return []float64{
		(latents[teams[0]].Offense - latents[teams[1]].Defense) - (latents[teams[1]].Offense - latents[teams[0]].Defense),
		math.Exp(latents[teams[0]].Offense - latents[teams[1]].Defense) - math.Exp(latents[teams[1]].Offense - latents[teams[0]].Defense),
		latents[teams[0]].Strength - latents[teams[1]].Strength,
		latents[teams[1]].Strength - latents[teams[0]].Strength,
		latents[teams[0]].Openness + latents[teams[1]].Openness,
	}
	// return poissonOutcomeProbs(math.Exp(latents[teams[0]].Offense - latents[teams[1]].Defense), math.Exp(latents[teams[1]].Offense - latents[teams[0]].Defense))
}

func errors(ps, target []float64) []float64 {
	errors := make([]float64, len(ps))

	for i, p := range ps {
		errors[i] = target[i] - p
	}

	return errors
}

func flip[T any](xs []T) []T {
	flipped := slices.Clone(xs)
	slices.Reverse(flipped)
	return flipped
}

func argmax(xs []float64) int {
	arg := 0

	for i, x := range xs {
		if x > xs[arg] {
			arg = i
		}
	}

	return arg
}

func loss(ps, target []float64) float64 {
	epsilon := 1e-15
	loss := 0.
	for i, p := range ps {
		p = math.Min(math.Max(p, epsilon), 1-epsilon)
		loss -= target[i] * math.Log(p)
	}

	return loss
}

func sigmoid(z float64) float64 {
	return 1 / (1 + math.Exp(-z))
}

func logFactorial(k int) float64 {
	lg, _ := math.Lgamma(float64(k + 1))
	return lg
}

func poissonPMF(k int, lambda float64) float64 {
	if lambda <= 0 {
		return 0
	}

	return math.Exp(float64(k)*math.Log(lambda) - lambda - logFactorial(k))
}

func poissonOutcomeProbs(lambda0, lambda1 float64) []float64 {
	probs := []float64{0, 0, 0}

	for g0 := 0; g0 <= 12; g0++ {
		p0 := poissonPMF(g0, lambda0)

		for g1 := 0; g1 <= 12; g1++ {
			p := p0 * poissonPMF(g1, lambda1)

			if g0 > g1 {
				probs[0] += p
			} else if g0 == g1 {
				probs[1] += p
			} else {
				probs[2] += p
			}
		}
	}

	sum := probs[0] + probs[1] + probs[2]
	for i := range probs {
		probs[i] /= sum
	}

	return probs
}

func main() {
	matches, err := readMatches(INPUT_PATH)
	if err != nil {
		panic(err)
	}

	model := lynn.NewLinearGroup(3, 5)

	numTestMatches := int(float64(len(matches)) * TEST_FRACTION)

	latents := map[string]*Latent{}

	numCorrect := 0
	logLoss := 0.

	for i := len(matches) - 1; i >= 0; i-- {
		match := matches[i]

		for _, team := range match.Teams {
			if _, ok := latents[team]; !ok {
				latents[team] = new(Latent)
			}
		}

		// update model
		xs := makeXs(latents, match.Teams)
		prediction := lynn.Softmax(model.Feed(xs))
		gradient := errors(prediction, match.Outcome)

		flipXs := makeXs(latents, flip(match.Teams))
		flipPrediction := lynn.Softmax(model.Feed(flipXs))
		flipGradient := errors(flipPrediction, flip(match.Outcome))

		model.Step(xs, gradient, MODEL_LEARNING_RATE)
		model.Step(flipXs, flipGradient, MODEL_LEARNING_RATE)

		// prediction := poissonOutcomeProbs(
		// 	math.Exp(latents[match.Teams[0]].Offense-latents[match.Teams[1]].Defense),
		// 	math.Exp(latents[match.Teams[1]].Offense-latents[match.Teams[0]].Defense),
		// )

		// record model metrics
		if i < numTestMatches {
			if argmax(prediction) == argmax(match.Outcome) {
				numCorrect++
			}

			logLoss += loss(prediction, match.Outcome)
		}

		// update latents
		logisticLogit := latents[match.Teams[0]].Strength - latents[match.Teams[1]].Strength
		logisticGradient := (1 - float64(argmax(match.Outcome))/2) - sigmoid(logisticLogit)
		logisticStep := logisticGradient * LATENT_STRENGTH_LEARNING_RATE * math.Sqrt(1+math.Abs(float64(match.Scores[0]-match.Scores[1])))

		latents[match.Teams[0]].Strength += logisticStep
		latents[match.Teams[1]].Strength -= logisticStep

		opennessLogit := latents[match.Teams[0]].Openness + latents[match.Teams[1]].Openness
		opennessGradient := float64(match.Scores[0] + match.Scores[1]) - opennessLogit
		opennessStep := opennessGradient * LATENT_OPENNESS_LEARNING_RATE

		latents[match.Teams[0]].Openness += opennessStep
		latents[match.Teams[1]].Openness += opennessStep

		for homeIndex, homeTeam := range match.Teams {
			awayTeam := match.Teams[(homeIndex+1)%2]

			poissonLogit := latents[homeTeam].Offense - latents[awayTeam].Defense// + latents[homeTeam].Openness + latents[awayTeam].Openness
			poissonGradient := float64(match.Scores[homeIndex]) - math.Exp(poissonLogit)
			poissonStep := poissonGradient * LATENT_POINTS_LEARNING_RATE

			latents[homeTeam].Offense += poissonStep
			latents[awayTeam].Defense -= poissonStep
			// latents[homeTeam].Openness += poissonStep * 0.01
		}
	}

	// print model metrics
	logLoss /= float64(numTestMatches)

	fmt.Printf("%.1f%% correct\n", 100*float64(numCorrect)/float64(numTestMatches))
	fmt.Printf("%.3f log loss\n", logLoss)

	// print hypothetical match prediction
	hypoTeams := os.Args[1:]
	if len(hypoTeams) == 0 {
		return
	}

	fmt.Println("\nHYPOTHETICAL MATCH:")

	// hypoPrediction := poissonOutcomeProbs(math.Exp(latents[hypoTeams[0]].Offense-latents[hypoTeams[1]].Defense), math.Exp(latents[hypoTeams[1]].Offense-latents[hypoTeams[0]].Defense))
	hypoPrediction := lynn.Softmax(model.Feed(makeXs(latents, hypoTeams)))
	fmt.Printf(
		"0) %s\t%.1f%%\n2) %s\t%.1f%%\n1) draw\t%.1f%%\n\n",
		hypoTeams[0], 100*hypoPrediction[0],
		hypoTeams[1], 100*hypoPrediction[2],
		100*hypoPrediction[1],
	)

	outcome := -1
	for outcome != 0 && outcome != 1 && outcome != 2 {
		fmt.Print("WHICH OUTCOME ARE YOU BETTING? [0/2/1] ")
		fmt.Scanf("%d", &outcome)
	}

	cost := -1.
	for cost < 0 || cost > 1 {
		fmt.Print("AT WHAT COST? ")
		fmt.Scanf("%f", &cost)
	}

	f := 100 * KELLY_MULTIPLIER * (1 - logLoss/math.Log(3)) * (hypoPrediction[outcome] - cost) / (1 - cost)
	if f <= 0 {
		fmt.Println("\ndon't bet")
	} else {
		fmt.Printf("\nbet %.1f%%\n", f)
	}
}
