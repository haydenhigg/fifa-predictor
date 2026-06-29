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

const LATENT_LEARNING_RATE = 0.22
const MODEL_LEARNING_RATE = 0.02
const TEST_FRACTION = 0.10
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
	Offense, Defense float64
}

func makeXs(latents map[string]*Latent, teams []string) []float64 {
	xs := make([]float64, 2*len(teams))

	for i, team := range teams {
		xs[2*i] = latents[team].Offense
		xs[2*i+1] = latents[team].Defense
	}

	diff0 := latents[teams[0]].Offense - latents[teams[1]].Defense
	diff1 := latents[teams[1]].Offense - latents[teams[0]].Defense

	return append(
		xs,
		diff0,
		diff1,
		diff0-diff1,
		math.Exp(diff0)-math.Exp(diff1),
	)
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

func main() {
	matches, err := readMatches(INPUT_PATH)
	if err != nil {
		panic(err)
	}

	latents := map[string]*Latent{}
	model := lynn.NewLinearGroup(3, 8)

	numTestMatches := int(float64(len(matches)) * TEST_FRACTION)
	numCorrect := 0

	logLoss := 0.

	for i := len(matches) - 1; i >= 0; i-- {
		match := matches[i]

		// update latents
		for _, team := range match.Teams {
			if _, ok := latents[team]; !ok {
				latents[team] = new(Latent)
			}
		}

		for homeIndex, homeTeam := range match.Teams {
			awayTeam := match.Teams[(homeIndex+1)%2]

			logit := latents[homeTeam].Offense - latents[awayTeam].Defense
			gradient := float64(match.Scores[homeIndex]) - math.Exp(logit)

			step := gradient * LATENT_LEARNING_RATE
			latents[homeTeam].Offense += step
			latents[awayTeam].Defense -= step
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

		// record model metrics
		if i < numTestMatches {
			if argmax(prediction) == argmax(match.Outcome) {
				numCorrect++
			}

			logLoss += loss(prediction, match.Outcome)
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
