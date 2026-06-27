package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"math"
	"os"
	"slices"
	"strconv"
	"time"
)

const INPUT_PATH = "fifa_matches.csv"
const LATENT_LEARNING_RATE = 0.05
const TEST_PORTION = 0.1

type Match struct {
	Date    time.Time
	Status  string
	Teams   []string
	Scores  []int
	Outcome float32
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

		outcome := float32(0.5)
		if homeScore > awayScore {
			outcome = 1
		} else {
			outcome = 0
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

func main() {
	matches, err := readMatches(INPUT_PATH)
	if err != nil {
		panic(err)
	}
	// numTestMatches := int(float64(len(matches)) * TEST_PORTION)

	latents := map[string]*Latent{}

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

			step := gradient * LATENT_LEARNING_RATE
			latents[homeTeam].Offense += step
			latents[awayTeam].Defense -= step
		}
	}

	teams := make([]string, len(latents))
	i := 0
	for team := range latents {
		teams[i] = team
		i++
	}

	slices.SortFunc(teams, func(a, b string) int {
		aTotal := latents[a].Offense + latents[a].Defense
		bTotal := latents[b].Offense + latents[b].Defense

		if aTotal < bTotal {
			return 1
		}

		return -1
	})

	for i := range 10 {
		latent := latents[teams[i]]
		fmt.Println(teams[i], latent.Offense+latent.Defense, latent)
	}
}
