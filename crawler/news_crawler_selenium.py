import argparse
import toml
import datetime
from random import uniform
from time import sleep
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotInteractableException


def get_article_urls(url: str, params: dict, driver, cnt: int = 0) -> list:
    get_url = url + '?'
    for param in params:
        get_url += param + '=' + str(params[param]) + '&'

    driver.get(get_url)
    sleep(uniform(1.5, 3.0))

    articles = driver.find_elements_by_css_selector("#main_content > div.list_body.newsflash_body > ul > li > a")
    article_url_list = [article.get_attribute('href') for article in articles]

    if (len(article_url_list) == 0) & (cnt < 4):
        print('GET FAIL RE GET', params)
        article_url_list = get_article_urls(url, params, driver, cnt=++cnt)

    return article_url_list


def get_comments(driver) -> list:
    driver.find_element_by_css_selector("#cbox_module > div > div.u_cbox_view_comment > a > "
                                        "span.u_cbox_in_view_comment").click()
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "u_cbox_list"))
        )
    except Exception as e:
        print(e)
        return []

    while True:
        try:
            driver.find_element_by_css_selector("#cbox_module > div > div.u_cbox_paginate > a > span > span "
                                                "> span.u_cbox_page_more").click()
            sleep(uniform(0.5, 1))
        except ElementNotInteractableException:
            break

    driver.execute_script("window.scrollTo(0, 0)")

    reply_comments = driver.find_elements_by_css_selector("#cbox_module > div > div.u_cbox_content_wrap > ul "
                                                          "> li.u_cbox_comment > div.u_cbox_comment_box > div "
                                                          "> div.u_cbox_tool > a > strong")

    for i in reply_comments:
        i.click()
        sleep(uniform(0.5, 1))

    comments_contents = driver.find_elements_by_class_name("u_cbox_area")

    comments = []
    for i in range(len(comments_contents)):
        comment = dict()
        parsed_comment = comments_contents[i].text.split('\n')
        comment['id'] = parsed_comment[0]
        if len(parsed_comment) == 11:
            comment['content'] = parsed_comment[3]
            comment['time'] = parsed_comment[4]
            comment['agree'] = parsed_comment[8]
            comment['opposition'] = parsed_comment[10]
        elif len(parsed_comment) == 10:
            comment['content'] = parsed_comment[3]
            comment['time'] = parsed_comment[4]
            comment['agree'] = parsed_comment[7]
            comment['opposition'] = parsed_comment[9]
        elif len(parsed_comment) == 5:
            comment['content'] = None
            comment['time'] = parsed_comment[4]
            comment['agree'] = None
            comment['opposition'] = None
        else:
            comment['content'] = None
            comment['time'] = parsed_comment[2]
            comment['agree'] = None
            comment['opposition'] = None
        comments.append(comment)

    return comments


def get_article(article_url: str, driver) -> dict:
    driver.get(article_url)
    sleep(uniform(1.5, 3.0))

    article = dict()

    article['title'] = driver.find_element_by_css_selector("#articleTitle")
    article['upload_time'] = driver.find_element_by_css_selector("#main_content > div.article_header "
                                                                 "> div.article_info > div > span:nth-child(1)")

    try:
        article['modified_time'] = driver.find_element_by_css_selector("#main_content > div.article_header "
                                                                   "> div.article_info > div > span:nth-child(2)")
    except NoSuchElementException:
        article['modified_time'] = None
    article['content'] = driver.find_element_by_css_selector("#articleBodyContents")

    article['category'] = driver.find_elements_by_css_selector("#articleBody > div.guide_categorization > a > em")
    article['category'] = [category.text for category in article['category']]

    try:
        article['comment_cnt'] = driver.find_element_by_css_selector("#cbox_module > div > div.u_cbox_head > a "
                                                                 "> span.u_cbox_count")
    except NoSuchElementException:
        article['comment_cnt'] = driver.find_element_by_css_selector("#cbox_module > div > h5 > em")

    article['recommendation_cnt'] = driver.find_element_by_css_selector("#toMainContainer > a > em.u_cnt._count")

    try:
        article['likeit_cnt'] = driver.find_element_by_css_selector("#main_content > div.article_header "
                                                                    "> div.article_info "
                                                                "> div > div.article_btns > div.article_btns_left "
                                                                "> div > a > span.u_likeit_text._count.num")
    except NoSuchElementException:
        article['likeit_cnt'] = 0

    article['good'] = driver.find_element_by_css_selector("#spiLayer > div._reactionModule.u_likeit > ul "
                                                          "> li.u_likeit_list.good > a "
                                                          "> span.u_likeit_list_count._count")
    article['warm'] = driver.find_element_by_css_selector("#spiLayer > div._reactionModule.u_likeit > ul "
                                                          "> li.u_likeit_list.warm > a "
                                                          "> span.u_likeit_list_count._count")
    article['sad'] = driver.find_element_by_css_selector("#spiLayer > div._reactionModule.u_likeit > ul "
                                                         "> li.u_likeit_list.sad > a > span.u_likeit_list_count._count")
    article['angry'] = driver.find_element_by_css_selector("#spiLayer > div._reactionModule.u_likeit > ul "
                                                           "> li.u_likeit_list.angry > a "
                                                           "> span.u_likeit_list_count._count")
    article['want'] = driver.find_element_by_css_selector("#spiLayer > div._reactionModule.u_likeit > ul "
                                                          "> li.u_likeit_list.want > a "
                                                          "> span.u_likeit_list_count._count")

    for prop in article:
        if hasattr(article[prop], 'text'):
            article[prop] = article[prop].text

    article['comment_cnt'] = int(article['comment_cnt'].encode('euc-kr'))

    if article['recommendation_cnt'].encode('euc-kr') == b'':
        article['recommendation_cnt'] = 0
    else:
        article['recommendation_cnt'] = int(article['recommendation_cnt'].encode('euc-kr'))

    article['likeit_cnt'] = int(article['likeit_cnt'])
    article['good'] = int(article['good'])
    article['warm'] = int(article['warm'])
    article['sad'] = int(article['sad'])
    article['angry'] = int(article['angry'])
    article['want'] = int(article['want'])

    if article['comment_cnt'] > 0:
        article['comments'] = get_comments(driver)

    return article


def get_article_id(article_url: str) -> int:
    regex = re.compile("(?<=aid=)\d+")
    article_id = regex.findall(article_url)
    return article_id[0]


def get_reporter_name(context: str) -> str:
    regex = re.compile("[가-횧]+(?= 기자)")
    reporter_name = regex.findall(context)
    try:
        return reporter_name[-1]
    except Exception:
        return None


def get_reporter_id(context: str) -> str:
    regex = re.compile("\w+(?=@kbs.co.kr)")
    reporter_email = regex.findall(context)
    try:
        return reporter_email[-1]
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser()

    # parameters
    parser.add_argument('--image_path', type=str, default='../images')

    # Config file parameters
    parser.add_argument('--config_file', '-c', type=str, default=None)

    args = parser.parse_args()

    if args.config_file:
        config = toml.load(args.config_file)
        for key_ in config:
            setattr(args, key_, config[key_])

    url = args.url
    date = args.date
    dates = args.dates
    params = args.parameters
    image_path = args.image_path

    driver = webdriver.Chrome('./chromedriver')
    driver.implicitly_wait(3)

    for days_ in range(dates):
        params['date'] = (date - datetime.timedelta(days=days_)).strftime("%Y%m%d")
        params['page'] = 0
        article_url_list = []

        while True:
            params['page'] += 1
            url_list = get_article_urls(url, params, driver=driver)

            try:
                if url_list[0] in article_url_list:
                    break
                else:
                    article_url_list.extend(url_list)
            except Exception as e:
                print('params:', params)
                print(e)

        print(params['date'], 'get', len(article_url_list), 'articles')

        for article_url in article_url_list:
            article = get_article(article_url, driver)
            article['id'] = get_article_id(article_url)
            article['reporter_name'] = get_reporter_name(article['content'])
            article['reporter_id'] = get_reporter_id(article['content'])
            print(article)


if __name__ == "__main__":
    main()