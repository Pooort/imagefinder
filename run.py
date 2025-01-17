import asyncio
import datetime
import logging
import os
import urllib
from time import sleep

import tqdm
from os.path import isfile, join

from pyppeteer import launch
from jinja2 import FileSystemLoader, Environment
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from config import LOWIMAGESPATH, HEADLESS, INFOFILE
from helpers import get_web_driver
from selenium.webdriver.support import expected_conditions as EC


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
    #bar = tqdm.tqdm(total=len(images_data))
    #bar.set_description(desc='Downloading images')
    downloaded_images_data = {}
    for file_path, image_hrefs in images_data.items():
        #bar.update()
        dir_name = os.path.basename(file_path).split('.')[0]
        image_dir_path = os.path.join(LOWIMAGESPATH, dir_name)
        image_dir = os.path.basename(image_dir_path)
        downloaded_images_data[image_dir] = []
        if not os.path.exists(image_dir_path):
            os.makedirs(image_dir_path)
        for i, image_href in enumerate(image_hrefs):
            try:
                file_extension = image_href.rsplit('.', 1)[1]
            except Exception as ex:
                print(ex)
                logger.warn('Problem with href: {}'.format(image_href))
            filename = '{}.{}'.format(i, file_extension)
            filepath = os.path.join(image_dir_path, filename)
            try:
                urllib.request.urlretrieve(image_href, filepath)
                inner_image_data = {'src': '{}'.format(os.path.join(dir_name, filename)), 'href': image_href}
                downloaded_images_data[image_dir].append(inner_image_data)
            except:
                logger.warning('Problem with downloading: {}'.format(image_href))
    return downloaded_images_data
    #bar.close()


def selenium_get_data(low_file_paths):
    browser = get_web_driver()
    bar = tqdm.tqdm(total=len(low_file_paths))
    bar.set_description(desc='Processing images')
    logger.info('Number of images to find: {}'.format(len(low_file_paths)))
    downloaded_images_data = {}
    for low_file_path in low_file_paths:
        bar.update()
        try:
            browser.get('https://www.google.com/imghp')
            logger.info('Page loaded: {}'.format(browser.current_url))
            browser.find_element_by_xpath('//span[@class="S3Wjs"]').click()

            wait = WebDriverWait(browser, 10)
            wait.until(EC.element_to_be_clickable((By.XPATH, '//form[@method="GET"]/div/div/a'))).click()
            browser.find_element_by_xpath('//input[@id="qbfile"]').send_keys(low_file_path)
            div_els = browser.find_elements_by_xpath('//div[@class="normal-header not-first"]/following-sibling::*')
            if len(div_els) == 0:
                continue
            else:
                div_el = div_els[0]
            a_els = div_el.find_elements_by_xpath('div/div/div/div/div[2]/div[1]/div/a')
            if not a_els:
                a_els = div_el.find_elements_by_xpath('div/div/div/div[2]/div[1]/div/a')
            if not a_els:
                a_els = div_el.find_elements_by_xpath('div/div[1]/div/div/div[2]/div[1]/div/a')
            big_image_hrefs = []
            image_sizes = set()
            for a_element in a_els:
                size = a_element.find_element_by_xpath('parent::*/parent::*/following-sibling::*/span/span').text
                if size in image_sizes:
                    continue
                image_sizes.add(size)
                full_image_href = a_element.get_attribute('href')
                image_href= full_image_href.split('imgres?imgurl=', 1)[1].split('&imgrefurl=', 1)[0]
                big_image_hrefs.append(image_href)
            download_image_data = download_images({low_file_path: big_image_hrefs})
            downloaded_images_data.update(download_image_data)
        except Exception as ex:
            print(ex)
            logger.warning('Problem with {}: {}'.format(low_file_path, ex))
        sleep(2)
    browser.quit()
    bar.close()
    return downloaded_images_data


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
            await page.goto('https://www.google.com/imghp')
            logger.info('Page loaded: {}'.format(page.url))
            els = await page.xpath('//span[@class="S3Wjs"]')
            await els[0].click()
            await page.waitForXPath('//form[@method="GET"]/div/div/a')
            a_els = await page.xpath('//form[@method="GET"]/div/div/a')
            await a_els[0].click()
            input_els = await  page.xpath('//input[@id="qbfile"]')
            #navigationPromise = asyncio.ensure_future(page.waitForNavigation())
            #await input_els[0].uploadFile(low_file_path)
            #sleep(1)
            #await page.waitForNavigation()
            try:
                await asyncio.gather(
                    input_els[0].uploadFile(low_file_path),
                    page.waitForNavigation()
                )
            except:
                page = await browser.newPage()
                continue
            #page.waitForXPath('//div[@class="normal-header not-first"]/following-sibling::*')
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
            download_images({low_file_path: big_image_hrefs})
        except Exception as ex:
            print(ex)
            logger.warning('Problem with {}: {}'.format(low_file_path, ex))
        sleep(2)
    await browser.close()
    bar.close()
    return result


def create_html(folders):
    loader = FileSystemLoader(searchpath=os.path.dirname(os.path.realpath(__file__)))
    env = Environment(loader=loader)
    TEMPLATE_FILE = "html.template"
    template = env.get_template(TEMPLATE_FILE)
    output = template.render(folders=folders)
    with open(INFOFILE, 'w') as infofile:
        infofile.write(output)
    return output

if __name__ == '__main__':
    start_time = datetime.datetime.now()
    logger.info('Script started at {}'.format(start_time))

    low_file_paths = [os.path.join(LOWIMAGESPATH, f) for f in os.listdir(LOWIMAGESPATH) if isfile(join(LOWIMAGESPATH, f)) and not os.path.exists(os.path.join(LOWIMAGESPATH, f.split('.')[0]))]

    if low_file_paths:
        images_data = selenium_get_data(low_file_paths)
        create_html(images_data)

    end_time = datetime.datetime.now()
    logger.info('Script ended at {}'.format(end_time))
