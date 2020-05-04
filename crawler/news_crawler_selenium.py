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
import requests
import shutil
import os
import pymysql
from tqdm import tqdm


# get articles' url during a day before crawling article
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


def get_comments(driver, article_id) -> list:
    try:
        driver.find_element_by_css_selector("#cbox_module > div > div.u_cbox_view_comment > a > "
                                        "span.u_cbox_in_view_comment").click()
    except NoSuchElementException as e:
        driver.find_element_by_css_selector("#cbox_module > div > div > "
                                            "a.simplecmt_link").click()

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
    """
    reply_comments = driver.find_elements_by_css_selector("#cbox_module > div > div.u_cbox_content_wrap > ul "
                                                          "> li.u_cbox_comment > div.u_cbox_comment_box > div "
                                                          "> div.u_cbox_tool > a > strong")
    """

    reply_comments = driver.find_elements_by_css_selector("#cbox_module > div > div.u_cbox_content_wrap > ul "
                                                          "> li.u_cbox_comment > div.u_cbox_comment_box > div "
                                                          "> div.u_cbox_tool > a > span.u_cbox_reply_cnt")

    for i in reply_comments:
        if i.text == "0":
            continue
        try:
            i.click()
            sleep(uniform(0.5, 1))
        except Exception as e:
            print(article_id, e)
            pass

    comments_contents = driver.find_elements_by_class_name("u_cbox_area")

    comments = []
    for i in range(len(comments_contents)):
        comment = dict()
        parsed_comment = comments_contents[i].text.split('\n')
        comment['user_id'] = parsed_comment[0]
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


def get_article(article_url: str, article_id: str, image_path: str, driver) -> dict:
    driver.get(article_url)
    sleep(uniform(1.5, 3.0))

    article = dict()

    try:
        article['title'] = driver.find_element_by_css_selector("#articleTitle")
    except NoSuchElementException:
        return article
        # driver.find_elements_by_class_name("title")

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

    article['img_path'] = []
    try:
        for i, img_src in enumerate(driver.find_elements_by_css_selector("span.end_photo_org > img")):
            img_res = requests.get(img_src.get_attribute('src'), stream=True)
            img_path = os.path.join(image_path, article_id+'_'+str(i)+'.jpg')
            with open(img_path, 'wb') as out_file:
                shutil.copyfileobj(img_res.raw, out_file)
            article['img_path'].append(img_path)
    except Exception as e:
        print(e)
        pass

    try:
        article['comment_cnt'] = int(article['comment_cnt'].encode('euc-kr'))
    except ValueError:
        article['comment_cnt'] = int(article['comment_cnt'].replace(',', ''))

    if article['recommendation_cnt'].encode('euc-kr') == b'':
        article['recommendation_cnt'] = 0
    else:
        article['recommendation_cnt'] = int(article['recommendation_cnt'].encode('euc-kr'))
    try:
        article['likeit_cnt'] = int(article['likeit_cnt'])
    except ValueError:
        article['likeit_cnt'] = int(article['likeit_cnt'].replace(',', ''))

    try:
        article['good'] = int(article['good'])
    except ValueError:
        article['good'] = int(article['good'].replace(',', ''))

    try:
        article['warm'] = int(article['warm'])
    except ValueError:
        article['warm'] = int(article['warm'].replace(',', ''))

    try:
        article['sad'] = int(article['sad'])
    except ValueError:
        article['sad'] = int(article['sad'].replace(',', ''))

    try:
        article['angry'] = int(article['angry'])
    except ValueError:
        article['angry'] = int(article['angry'].replace(',', ''))

    try:
        article['want'] = int(article['want'])
    except ValueError:
        article['want'] = int(article['want'].replace(',', ''))

    if article['comment_cnt'] > 0:
        article['comments'] = get_comments(driver, article_id)

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


# check db before crawl article
def check_db(db, article_id) -> int:
    with db.cursor() as cursor:
        cursor.execute(f'select count(*) from articles where id = {article_id}')
        result = cursor.fetchone()
    return result[0]


# insert article and comment data to db
def insert_db(db, article: dict):
    article['category'] = ' '.join(article['category'])
    comments = article.pop('comments', None)
    img_paths = article.pop('img_path', None)

    cols = ', '.join(article)
    placeholders = ', '.join(['%s'] * len(article))

    with db.cursor() as cursor:
        cursor.execute(f"insert into articles ({cols}) values ({placeholders})", tuple(article.values()))
        db.commit()

    if comments:
        for comment in comments:
            comment['article_id'] = article['id']
            cols = ', '.join(comment)
            placeholders = ', '.join(['%s'] * 6)

            with db.cursor() as cursor:
                cursor.execute(f"insert into comments ({cols}) values ({placeholders})", tuple(comment.values()))
                db.commit()

    if img_paths:
        for img_path in img_paths:
            with db.cursor() as cursor:
                cursor.execute(f"insert into images (article_id, img_path) "
                               f"values (\'{article['id']}\', \'{img_path}\')")
                db.commit()


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
    db_info = args.db
    image_path = os.path.abspath(args.image_path)

    driver = webdriver.Chrome('./chromedriver')
    driver.implicitly_wait(3)

    db = pymysql.connect(host=db_info['host'], port=db_info['port'], user=db_info['user'],
                         passwd=db_info['password'], db=db_info['db'], charset='utf8')

    for days_ in tqdm(range(dates), desc="DAYS"):
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

        for article_url in tqdm(article_url_list, desc=f"Collecting Articles in {params['date']}", leave=False):
            article_id = get_article_id(article_url)
            if not check_db(db, article_id):
                article = get_article(article_url, article_id, image_path, driver)
                if not article:
                    continue
                article['id'] = article_id
                article['reporter_name'] = get_reporter_name(article['content'])
                article['reporter_id'] = get_reporter_id(article['content'])
                insert_db(db, article)


if __name__ == "__main__":
    main()