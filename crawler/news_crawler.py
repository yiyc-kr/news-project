import argparse
import toml
import datetime
import requests
from fake_useragent import UserAgent
from random import uniform
from time import sleep
from bs4 import BeautifulSoup
from bs4 import element
import re


def get_article_urls(url: str, params: dict, cnt: int = 0) -> list:
    get_url = url + '?'
    for param in params:
        get_url += param + '=' + str(params[param]) + '&'

    req = requests.get(get_url, headers={"User-Agent": UserAgent().random})
    sleep(uniform(1.5, 3.0))

    soup = BeautifulSoup(req.content, "html.parser")
    articles = soup.select('#main_content > div.list_body.newsflash_body > ul > li > a')
    article_url_list = [article.attrs['href'] for article in articles]

    if (len(article_url_list) == 0) & (cnt < 4):
        print('GET FAIL RE GET', params)
        article_url_list = get_article_urls(url, params, ++cnt)

    return article_url_list


def get_article(article_url: str) -> dict:
    req = requests.get(article_url, headers={"User-Agent": UserAgent().random})
    sleep(uniform(1.5, 3.0))

    soup = BeautifulSoup(req.content, "html.parser")

    article = dict()

    article['title'] = soup.select_one("#articleTitle")
    article['upload_time'] = \
        soup.select_one("#main_content > div.article_header > div.article_info > div > span:nth-child(1)")
    article['modified_time'] = \
        soup.select_one("#main_content > div.article_header > div.article_info > div > span:nth-child(2)")
    article['context'] = soup.select_one("#articleBodyContents")
    article['category'] = soup.select_one("#articleBody > div.guide_categorization > a > em")
    article['comment_cnt'] = soup.select_one("#cbox_module > div > div.u_cbox_head > a > span.u_cbox_count")
    article['recommendation_cnt'] = soup.select_one("#toMainContainer > a > em.u_cnt._count")
    article['likeit_cnt'] = soup.select_one("#main_content > div.article_header > div.article_info > div "
                        "> div.article_btns > div.article_btns_left > div > a > span.u_likeit_text._count.num")
    article['good'] = soup.select_one("#spiLayer > div._reactionModule.u_likeit > ul > li.u_likeit_list.good > a "
                                      "> span.u_likeit_list_count._count")
    article['warm'] = soup.select_one("#spiLayer > div._reactionModule.u_likeit > ul > li.u_likeit_list.warm > a "
                                      "> span.u_likeit_list_count._count")
    article['sad'] = soup.select_one("#spiLayer > div._reactionModule.u_likeit > ul > li.u_likeit_list.sad > a "
                                     "> span.u_likeit_list_count._count")
    article['angry'] = soup.select_one("#spiLayer > div._reactionModule.u_likeit > ul > li.u_likeit_list.angry > a "
                                       "> span.u_likeit_list_count._count")
    article['want'] = soup.select_one("#spiLayer > div._reactionModule.u_likeit > ul > li.u_likeit_list.want > a "
                                      "> span.u_likeit_list_count._count")

    for prop in article:
        if type(article[prop]) is element.Tag:
            article[prop] = article[prop].text

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

    for days_ in range(dates):
        params['date'] = (date - datetime.timedelta(days=days_)).strftime("%Y%m%d")
        params['page'] = 0
        article_url_list = []

        while True:
            params['page'] += 1
            url_list = get_article_urls(url, params)

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
            article = get_article(article_url)
            article['id'] = get_article_id(article_url)
            article['reporter_name'] = get_reporter_name(article['context'])
            article['reporter_id'] = get_reporter_id(article['context'])
            print(article)


if __name__ == "__main__":
    main()