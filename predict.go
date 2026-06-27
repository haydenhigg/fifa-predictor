package main

import (
	"encoding/csv"
	"fmt"
	"github.com/haydenhigg/lynn"
	"io"
	"math"
	"os"
	"strconv"
	"time"
)

const INPUT_PATH = "fifa_matches.csv"

const LEARNING_RATE = 0.1
const TEST_FRACTION = 0.05

type Match struct {
	Date    time.Time
	Status  string
	Teams   []string
	Scores  []int
	Outcome []float64
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
			Date:    date,
			Status:  record[1],
			Teams:   []string{record[2], record[4]},
			Scores:  []int{homeScore, awayScore},
			Outcome: outcome,
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

	return xs
}

func errors(ps, target []float64) []float64 {
	errors := make([]float64, len(ps))

	for i, p := range ps {
		errors[i] = target[i] - p
	}

	return errors
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

func main() {
	matches, err := readMatches(INPUT_PATH)
	if err != nil {
		panic(err)
	}

	latents := map[string]*Latent{}
	model := lynn.NewLinearGroup(3, 4)

	numTestMatches := int(float64(len(matches)) * TEST_FRACTION)
	numCorrect := 0

	for i := len(matches) - 1; i >= 0; i-- {
		match := matches[i]

		// update latents
		for _, team := range match.Teams {
			if _, ok := latents[team]; !ok {
				latents[team] = new(Latent)
			}
		}

		for home, homeTeam := range match.Teams {
			awayTeam := match.Teams[(home+1)%2]

			logit := latents[homeTeam].Offense - latents[awayTeam].Defense
			gradient := float64(match.Scores[home]) - math.Exp(logit)

			step := gradient * LEARNING_RATE
			latents[homeTeam].Offense += step
			latents[awayTeam].Defense -= step
		}

		// update model
		xs := makeXs(latents, match.Teams)

		prediction := lynn.Softmax(model.Feed(xs))
		gradient := errors(prediction, match.Outcome)
		model.Step(xs, gradient, LEARNING_RATE)

		fmt.Println(match.Outcome, prediction)

		// record model metrics
		if i < numTestMatches {
			if argmax(prediction) == argmax(match.Outcome) {
				numCorrect++
			}
		}
	}

	// print model metrics
	fmt.Printf("\n%.1f%% correct\n", 100*float64(numCorrect)/float64(numTestMatches))
	fmt.Printf("%.3f log loss\n", 0.)

	// print hypothetical match prediction
	fmt.Println("\nHYPOTHETICAL MATCH:")
	hypo := []string{"Colombia", "Portugal"}
	hypoPrediction := lynn.Softmax(model.Feed(makeXs(latents, hypo)))

	fmt.Printf(
		"%s\t%.0f%%\n%s\t%.0f%%\nDraw\t\t%.0f%%\n",
		hypo[0], 100*hypoPrediction[0],
		hypo[1], 100*hypoPrediction[2],
		100*hypoPrediction[1],
	)
}
