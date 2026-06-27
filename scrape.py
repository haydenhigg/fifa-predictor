from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep
import csv

URL = 'https://inside.fifa.com/data-centre/matches'
OUTPUT_PATH = Path('fifa_matches.csv')

def build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    return webdriver.Chrome(options=options)

def dismiss_cookie_banner(driver: webdriver.Chrome):
    to_be_button = EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler'))
    button = WebDriverWait(driver, 5).until(to_be_button)
    button.click()

def get_rows(driver: webdriver.Chrome) -> list:
    row_elements = driver.find_elements(By.CSS_SELECTOR, 'table tbody tr')
    rows: list = []

    for element in row_elements:
        date = element.find_elements(By.CSS_SELECTOR, 'td:first-child')[-1]

        match_element = element.find_elements(By.CSS_SELECTOR, 'td:nth-child(2)')[-1]
        status = match_element.find_elements(By.CSS_SELECTOR, 'div.match-cell-status span')[-1]
        teams = match_element.find_elements(By.CSS_SELECTOR, 'div.match-cell-teams span')
        scores = match_element.find_elements(By.CSS_SELECTOR, 'div.match-cell-scores span')

        rows.append((
            date.text,
            status.text,
            teams[0].text,
            scores[0].text.strip('()'),
            teams[1].text,
            scores[1].text.strip('()')
        ))

    return rows

def click_show_more(driver: webdriver.Chrome):
    to_be_button = EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Show more"]'))
    button = WebDriverWait(driver, 5).until(to_be_button)

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
    sleep(2)

    button.click()

if __name__ == '__main__':
    print('loading saved rows')
    rows = []
    if OUTPUT_PATH.is_file():
        with OUTPUT_PATH.open('r') as f:
            rows.extend([tuple(row) for row in csv.reader(f)])

    try:
        print('starting driver')
        driver = build_driver()

        print('getting page')
        driver.get(URL)

        print('dismissing cookie banner')
        dismiss_cookie_banner(driver)

        print('waiting for get_rows')
        WebDriverWait(driver, 5).until(lambda d: get_rows(d))

        while True:
            new_rows = get_rows(driver)
            rows_added = 0

            for row in new_rows:
                if row not in rows:
                    rows.append(row)
                    rows_added += 1

            with OUTPUT_PATH.open('w') as f:
                csv.writer(f).writerows(rows)

            print(f'saved {rows_added}/{len(new_rows)} new rows ({len(rows)} total)')

            click_show_more(driver)
            sleep(5)
    except:
        print('something went wrong')
        pass
    finally:
        print('quitting')
        driver.quit()
