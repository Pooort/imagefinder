import asyncio
import datetime
import logging
import os
import urllib
from time import sleep

import tqdm
from os.path import isfile, join

from pyppeteer import launch
from config import LOWIMAGESPATH, HEADLESS


def get_logger(level_name='DEBUG'):
    logger = logging.getLogger('Main')
    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    level = logging.getLevelName(level_name)
    logger.setLevel(level)

    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'logs')

    fileHandler = logging.FileHandler(file_path)
    fileHandler.setFormatter(logFormatter)
    logger.addHandler(fileHandler)

    #console_handler = logging.StreamHandler()
    #logger.addHandler(console_handler)

    return logger


logger = get_logger()


def download_images(images_data):
    bar = tqdm.tqdm(total=len(images_data))
    bar.set_description(desc='Downloading images')
    for file_path, image_hrefs in images_data.items():
        bar.update()
        for i, image_href in enumerate(image_hrefs):
            image_dir_path = os.path.join(LOWIMAGESPATH, os.path.basename(file_path).split('.')[0])
            if not os.path.exists(image_dir_path):
                os.makedirs(image_dir_path)
            file_extension = image_href.rsplit('.', 1)[1]
            filepath = os.path.join(image_dir_path, '{}.{}'.format(i, file_extension))
            try:
                urllib.request.urlretrieve(image_href, filepath)
            except:
                logger.warning('Problem with downloading: {}'.format(image_href))
    bar.close()


def selenium_get_data(low_file_paths):
    pass

async def get_data(low_file_paths):
    browser = await launch(headless=HEADLESS, args=['--no-sandbox'])
    page = await browser.newPage()
    await page.setUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.96 Safari/537.36')
    await page.evaluateOnNewDocument("() => {    Object.defineProperty(navigator, 'webdriver', {      get: () => false,    });  }")
    await page.evaluateOnNewDocument("() => {Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en'],});}")
    result = {}
    bar = tqdm.tqdm(total=len(low_file_paths))
    bar.set_description(desc='Processing images')
    logger.info('Number of images to find: {}'.format(len(low_file_paths)))
    for low_file_path in low_file_paths:
        bar.update()
        try:
            await page.goto('https://www.google.com/imghp', {
                'timeout': 3000000
            })
            logger.info('Page loaded: {}'.format(page.url))
            els = await page.xpath('//span[@class="S3Wjs"]')
            await els[0].click()
            await page.waitForXPath('//form[@method="GET"]/div/div/a')
            a_els = await page.xpath('//form[@method="GET"]/div/div/a')
            await a_els[0].click()
            input_els = await  page.xpath('//input[@id="qbfile"]')
            await input_els[0].uploadFile(low_file_path)
            await page.waitForNavigation()
            div_els = await page.xpath('//div[@class="normal-header not-first"]/following-sibling::*')
            a_els = await div_els[0].xpath('div/div/div/div/div[2]/div[1]/div/a')
            if not a_els:
                a_els = await div_els[0].xpath('div/div/div/div[2]/div[1]/div/a')
            if not a_els:
                a_els = await div_els[0].xpath('div/div[1]/div/div/div[2]/div[1]/div/a')
            big_image_hrefs = []
            for a_element in a_els:
                full_image_href = await a_element.getProperty('href')
                json_full_image_href = await full_image_href.jsonValue()
                image_href = json_full_image_href.split('imgres?imgurl=', 1)[1].split('&imgrefurl=', 1)[0]
                big_image_hrefs.append(image_href)
            result[low_file_path] = big_image_hrefs
        except Exception as ex:
            logger.warning('Problem with {}: {}'.format(low_file_path, ex))
        sleep(2)
    await browser.close()
    bar.close()
    return result


start_time = datetime.datetime.now()
logger.info('Script started at {}'.format(start_time))

low_file_paths = [os.path.join(LOWIMAGESPATH, f) for f in os.listdir(LOWIMAGESPATH) if isfile(join(LOWIMAGESPATH, f)) and not os.path.exists(os.path.join(LOWIMAGESPATH, f.split('.')[0]))]

if low_file_paths:
    images_data = asyncio.get_event_loop().run_until_complete(get_data(low_file_paths))

download_images(images_data)

end_time = datetime.datetime.now()
logger.info('Script ended at {}'.format(end_time))
