import os

from selenium import webdriver

from config import HEADLESS


def get_web_driver(headless=HEADLESS):

    chop = webdriver.ChromeOptions()

    if headless:
        chop.add_argument('--headless')
        chop.add_argument('--disable-gpu')

    chop.add_argument('--window-size=1280x1696')
    chop.add_argument('--ignore-certificate-errors')
    chop.add_argument('--no-sandbox')
    chop.add_argument('--disable-dev-shm-usage')


    file_path = os.path.dirname(os.path.realpath(__file__))

    chromedriver = os.path.join(file_path, 'chromedriver')
    driver = webdriver.Chrome(chromedriver, options=chop)

    return driver
