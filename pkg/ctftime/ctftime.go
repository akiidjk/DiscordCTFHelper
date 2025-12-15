package ctftime

import (
	"encoding/json"
	"image/png"
	"math/rand"
	"net/http"
	"strconv"

	"github.com/charmbracelet/log"
)

const BASE_URL = "https://ctftime.org/api/v1"

var USER_AGENT_LIST = []string{
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.5 Safari/605.1.15",
	"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36",
	"Mozilla/5.0 (Windows NT 10.0; Windows; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8",
	"Mozilla/5.0 (Windows NT 10.0; Windows; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
	"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
	"Mozilla/5.0 (Windows NT 10.0; Windows; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36",
	"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36",
}

func pickRandomAgent() string {
	return USER_AGENT_LIST[rand.Intn(len(USER_AGENT_LIST))]
}

func createRequest(url string) (*http.Request, error) {
	req, err := http.NewRequest("GET", url, nil)

	if err == nil {
		req.Header.Set("User-Agent", pickRandomAgent())
	}
	if err != nil {
		log.Error("Error creating request:", "err", err)
		return nil, err
	}
	return req, nil
}

func GetLogo(url string) ([]byte, error) {
	client := &http.Client{}
	req, err := createRequest(url)

	resp, err := client.Do(req)
	if err != nil {
		log.Error("Error sending request:", "err", err)
		return nil, err
	}
	defer resp.Body.Close()

	_, err = png.Decode(resp.Body)
	if err != nil {
		log.Error("Error decoding image:", "err", err)
		return nil, err
	}

	var image []byte
	resp.Body.Read(image)

	// Return the image bytes
	return image, nil
}

func GetCTFInfo(ctftime_id int) (Event, error) {
	idParsed := strconv.Itoa(ctftime_id)
	url := BASE_URL + "/events/" + idParsed + "/"
	client := &http.Client{}
	req, err := createRequest(url)

	resp, err := client.Do(req)
	if err != nil {
		log.Error("Error sending request:", "err", err)
		return Event{}, err
	}
	defer resp.Body.Close()

	var parsedJson Event
	var jsonResponse []byte
	_, err = resp.Body.Read(jsonResponse)
	if err != nil {
		return Event{}, err
	}

	if resp.StatusCode == 200 {
		json.Unmarshal(jsonResponse, &parsedJson)
	}

	return parsedJson, nil
}

func GetCTFs() ([]Event, error) {
	url := BASE_URL + "/events/"
	client := &http.Client{}
	req, err := createRequest(url)

	resp, err := client.Do(req)
	if err != nil {
		log.Error("Error sending request:", "err", err)
		return nil, err
	}
	defer resp.Body.Close()

	var parsedJson []Event
	var jsonResponse []byte
	_, err = resp.Body.Read(jsonResponse)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode == 200 {
		json.Unmarshal(jsonResponse, &parsedJson)
	}

	return parsedJson, nil
}
