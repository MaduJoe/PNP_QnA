import time
from selenium import webdriver
import csv
import pandas as pd
from bs4 import BeautifulSoup as bs
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

def parse_message(input_text):
    cleaned_text = re.sub(r'\s+', ' ', input_text.strip())
    return cleaned_text

total_list = ["제목", "내용", "댓글"]

# 초기 CSV 파일 생성
f = open('crawl_faq.csv', 'w', encoding="utf-8-sig", newline='')
wr = csv.writer(f)
wr.writerow(total_list)
f.close()

i = 0 # 1페이지 부터 
while True:
    origin_df = pd.read_csv('crawl_faq.csv', encoding='utf-8-sig')

    url = 'https://nid.naver.com/nidlogin.login'
    id = ""
    pw = ""

    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    driver_path = r'C:/chromedriver-win64/chromedriver.exe'
    service = Service(driver_path)
    browser = webdriver.Chrome(service=service, options=chrome_options)
    browser.get(url)
    browser.implicitly_wait(10)

    browser.execute_script(f"document.getElementsByName('id')[0].value='{id}'")
    browser.execute_script(f"document.getElementsByName('pw')[0].value='{pw}'")
    browser.find_element(by=By.XPATH, value='//*[@id="log.login"]').click()
    time.sleep(2)

    baseurl = 'https://cafe.naver.com'
    browser.get(baseurl)
    i += 1

    clubid = 29308153 #전체글보기
    boardtype = "L"
    pageNum = i
    userDisplay = 50
    print(f"pageNum : {pageNum}")

    # browser.get(baseurl + f'/ArticleList.nhn?search.clubid={clubid}&search.boardtype={boardtype}&search.page={pageNum}&userDisplay={userDisplay}')    #전체글보기 
    browser.get(baseurl + f'/ArticleList.nhn?search.clubid={clubid}&search.menuid=1236&search.boardtype={boardtype}&search.page={pageNum}&userDisplay={userDisplay}')   #FAQ(기술관련질의)
    browser.switch_to.frame('cafe_main')  # iframe 접근

    soup = bs(browser.page_source, 'html.parser')
    elements = soup.find_all(class_='article-board m-tcol-c')[1]
    datas = elements.select("#main-area > div:nth-child(4) > table > tbody > tr")

    for data in datas:
        article_title = data.find(class_="article")
        if article_title:
            article_title_text = parse_message(article_title.get_text())
            article_href = f"{baseurl}{article_title['href']}"
        else:
            article_title_text = "null"
            article_href = None

        # 기사 내용 및 댓글 가져오기
        if article_href:
            browser.get(article_href)
            try:
                browser.switch_to.frame('cafe_main')  # iframe 전환 필요 시
            except:
                pass

            try:
                WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'article_viewer')))
                article_page = bs(browser.page_source, 'html.parser')
                article_viewer = article_page.find(class_='article_viewer')
                comment_box = article_page.find(class_='CommentBox')

                article_content = parse_message(article_viewer.get_text()) if article_viewer else "null"
                article_comments = parse_message(comment_box.get_text()) if comment_box else "null"
                article_comments = article_comments.strip("댓글을 입력하세요조재근 등록").strip("댓글 등록순 최신순 새로고침관심글 댓글 알림등록 이 글에 새 댓글이 등록되면 내소식에서 알림을 받을 수 있습니다.").strip("댓글 등록순 최신순 새로고침관심글 댓글 알림등록 이 글에 새 댓글이 등록되면 내소식에서 알림을 받을 수 있습니다.").strip("답글쓰기")

            except:
                article_content = "null"
                article_comments = "null"

        else:
            article_content = "null"
            article_comments = "null"

        # CSV 파일에 저장
        with open('crawl_faq.csv', 'a+', newline='', encoding="utf-8-sig") as f:
            wr = csv.writer(f)
            wr.writerow([article_title_text, article_content, article_comments])

    print('종료')
    browser.quit()


