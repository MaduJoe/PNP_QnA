import time
import json
import csv
import logging
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import random

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NaverCafeCrawler:
    def __init__(self):
        self.naver_id = "pnp_jkcho"
        self.naver_pw = "100djrqjsek!"
        self.cafe_id = 29308153
        self.cafe_name = "pnpsecure2"  # 사용자 제공 실제 카페명
        self.menu_id = 64
        self.max_articles = 93  # 1페이지(18개) + 5페이지(15개씩) = 93개
        self.driver = None
        
    def setup_driver(self):
        """최신 네이버 카페 크롤링에 최적화된 드라이버 설정"""
        options = Options()
        
        # 2025년 네이버 우회를 위한 고급 설정
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 실제 사용자처럼 보이도록 하는 설정
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins-discovery")
        options.add_argument("--disable-web-security")
        
        # User-Agent 설정 (최신 Chrome)
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        options.add_argument(f"--user-agent={user_agent}")
        
        # 추가 보안 우회 설정
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        # JavaScript로 webdriver 속성 숨기기
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": user_agent
        })
        
        logger.info("드라이버 설정 완료")
        
    def random_delay(self, min_sec=1, max_sec=3):
        """인간적인 지연 시간"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        
    def naver_login(self):
        """네이버 로그인 (crawl_pc.py 방식)"""
        try:
            logger.info("네이버 로그인 시작...")
            self.driver.get("https://nid.naver.com/nidlogin.login")
            time.sleep(3)
            
            # JavaScript로 직접 값 설정 (crawl_pc.py 방식)
            self.driver.execute_script(f"document.getElementById('id').value='{self.naver_id}';")
            self.driver.execute_script(f"document.getElementById('pw').value='{self.naver_pw}';")
            time.sleep(2)
            
            # 로그인 버튼 클릭
            self.driver.find_element(By.ID, 'log.login').click()
            time.sleep(5)
            
            logger.info("네이버 로그인 완료")
            return True
                
        except Exception as e:
            logger.error(f"네이버 로그인 실패: {e}")
            return False
    
    def get_article_list(self, page=1): #3페이지부터 가져오기 
        """게시글 목록 가져오기 (2025년 버전)"""
        article_ids = []
        
        try:
            # 여러 URL 패턴 시도
            url_patterns = [
                f"https://cafe.naver.com/f-e/cafes/{self.cafe_id}/menus/{self.menu_id}?page={page}",
                f"https://cafe.naver.com/ArticleList.nhn?search.clubid={self.cafe_id}&search.menuid={self.menu_id}&search.boardtype=L&search.page={page}",
                f"https://cafe.naver.com/ca-fe/cafes/{self.cafe_id}/menus/{self.menu_id}?page={page}"
            ]
            
            success_url = None
            for url_pattern in url_patterns:
                try:
                    logger.info(f"URL 시도: {url_pattern}")
                    self.driver.get(url_pattern)
                    time.sleep(5)
                    
                    # 페이지 에러 확인
                    if "페이지를 찾을 수 없습니다" not in self.driver.page_source and "404" not in self.driver.page_source:
                        success_url = url_pattern
                        logger.info(f"성공한 URL: {success_url}")
                        break
                    else:
                        logger.warning(f"URL 실패: {url_pattern}")
                        
                except Exception as e:
                    logger.warning(f"URL {url_pattern} 접근 실패: {e}")
                    continue
            
            if not success_url:
                logger.error(f"모든 URL 패턴 실패 (페이지 {page})")
                return []
            
            self.random_delay(3, 5)
            
            # 페이지 완전 로딩 대기
            WebDriverWait(self.driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # iframe 없이 메인 페이지에서 먼저 시도
            logger.info("먼저 메인 페이지에서 콘텐츠 확인")
            time.sleep(3)
            
            # 페이지가 완전히 로드될 때까지 대기
            try:
                # JavaScript 실행이 완료될 때까지 대기
                WebDriverWait(self.driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                # 추가로 Ajax 요청이 완료될 때까지 대기
                time.sleep(5)
                
            except Exception as e:
                logger.warning(f"페이지 로딩 대기 실패: {e}")
            
            # 메인 페이지에서 iframe 다시 찾기
            iframe_switched = False
            try:
                # 다시 iframe 목록 확인 (동적으로 생성될 수 있음)
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                logger.info(f"페이지 로드 후 총 {len(iframes)}개 iframe 발견")
                
                for i, iframe in enumerate(iframes):
                    iframe_name = iframe.get_attribute('name')
                    iframe_id = iframe.get_attribute('id')
                    iframe_src = iframe.get_attribute('src')
                    iframe_title = iframe.get_attribute('title')
                    logger.info(f"iframe {i}: name='{iframe_name}', id='{iframe_id}', title='{iframe_title}', src='{iframe_src[:100] if iframe_src else None}'")
                    
                    # cafe_main 이름을 가진 iframe 우선 찾기
                    if iframe_name == 'cafe_main':
                        try:
                            self.driver.switch_to.frame(iframe)
                            logger.info(f"cafe_main iframe 전환 성공")
                            iframe_switched = True
                            break
                        except:
                            continue
                    
                    # 카페 관련 src를 가진 iframe 찾기
                    if iframe_src and ('cafe' in iframe_src or 'menu' in iframe_src or 'article' in iframe_src):
                        try:
                            self.driver.switch_to.frame(iframe)
                            logger.info(f"카페 관련 iframe {i} 전환 성공 (src: {iframe_src[:100]})")
                            iframe_switched = True
                            break
                        except:
                            continue
                
                # 여전히 찾지 못했으면 메인 페이지에서 진행
                if not iframe_switched:
                    logger.warning("적절한 iframe을 찾지 못함, 메인 페이지에서 진행")
                
            except Exception as e:
                logger.warning(f"iframe 처리 실패: {e}")
                
            # iframe 전환 후 추가 대기
            if iframe_switched:
                time.sleep(3)
            
            # 페이지 소스 저장 (디버깅용)
            with open(f"debug_list_page_{page}.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            
            # 페이지 소스에서 게시글 구조 확인 (디버깅)
            page_source = self.driver.page_source
            if 'class="article"' in page_source:
                logger.info("페이지 소스에 class='article' 태그가 존재합니다")
                article_count = page_source.count('class="article"')
                logger.info(f"총 {article_count}개의 article 클래스 태그 발견")
            else:
                logger.warning("페이지 소스에 class='article' 태그가 없습니다")
            
            # 테이블 행 확인
            if 'type_articleNumber' in page_source:
                logger.info("페이지 소스에 type_articleNumber 클래스가 존재합니다")
                article_num_count = page_source.count('type_articleNumber')
                logger.info(f"총 {article_num_count}개의 게시글 번호 발견")
            
            # 직접 tr 요소들 확인
            try:
                tr_elements = self.driver.find_elements(By.TAG_NAME, "tr")
                logger.info(f"총 {len(tr_elements)}개의 tr 요소 발견")
                
                # 게시글이 포함된 tr 찾기
                article_trs = self.driver.find_elements(By.XPATH, "//tr[td[@class='td_normal type_articleNumber']]")
                logger.info(f"게시글 번호가 포함된 tr: {len(article_trs)}개")
                
                if article_trs:
                    # 첫 번째 게시글 tr의 정보 출력
                    first_tr = article_trs[0]
                    article_num = first_tr.find_element(By.CLASS_NAME, "type_articleNumber").text
                    logger.info(f"첫 번째 게시글 번호: {article_num}")
                    
                    # 해당 tr에서 링크 찾기
                    links_in_tr = first_tr.find_elements(By.TAG_NAME, "a")
                    logger.info(f"첫 번째 tr에서 발견된 링크 수: {len(links_in_tr)}")
                    for i, link in enumerate(links_in_tr):
                        href = link.get_attribute('href')
                        class_name = link.get_attribute('class')
                        text = link.text[:50]
                        logger.info(f"링크 {i}: class='{class_name}', href='{href}', text='{text}'")
                        
            except Exception as e:
                logger.warning(f"tr 요소 직접 확인 실패: {e}")
            
            # 실제 HTML 구조에 맞는 정확한 선택자 (이미지 기반)
            selectors_to_try = [
                "table.article-table tbody tr",  # 이미지에서 확인한 정확한 구조
                ".article-board table.article-table tbody tr",  # 더 구체적인 경로
                ".cafe_content table.article-table tbody tr",  # 최상위부터
                "div.article-board table tbody tr",  # div.article-board 기준
                "table.article-table tr",  # 간단한 버전
            ]
            
            for selector in selectors_to_try:
                try:
                    tr_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"선택자 '{selector}': {len(tr_elements)}개 tr 요소 발견")
                    
                    if tr_elements:
                        for i, tr in enumerate(tr_elements):
                            try:
                                # tr 안에서 게시글 링크 찾기
                                article_links = tr.find_elements(By.CSS_SELECTOR, "a.article")
                                if not article_links:
                                    # 다른 링크 패턴도 시도
                                    article_links = tr.find_elements(By.CSS_SELECTOR, "a[href*='/articles/']")
                                
                                if article_links:
                                    article_link = article_links[0]  # 첫 번째 링크 사용
                                    href = article_link.get_attribute('href')
                                    
                                    if href and '/articles/' in href:
                                        # menu_id 필터링 확인
                                        if f"menuid={self.menu_id}" in href or f"&menuid={self.menu_id}" in href:
                                            # 게시글 ID 추출
                                            match = re.search(r'/articles/(\d+)', href)
                                            if match:
                                                article_id = int(match.group(1))
                                                
                                                # 제목 추출 (링크 텍스트에서)
                                                title = article_link.text.strip()
                                                if not title:
                                                    # 다른 방법으로 제목 찾기
                                                    title_elem = tr.find_element(By.CSS_SELECTOR, "a.article")
                                                    title = title_elem.get_attribute('title') or title_elem.text.strip()
                                                
                                                article_ids.append(article_id)
                                                logger.info(f"tr {i}에서 게시글 발견: ID={article_id}")
                                                logger.info(f"제목: {title[:50]}...")
                                                logger.info(f"URL: {href}")
                                                
                                                # 페이지당 15개 제한
                                                if len(article_ids) >= 15:
                                                    logger.info("페이지당 15개 제한에 도달")
                                                    break
                                        else:
                                            logger.debug(f"menu_id 불일치로 스킵: {href}")
                                             
                            except Exception as e:
                                logger.debug(f"tr {i} 처리 실패: {e}")
                                continue
                        
                        # 15개 도달 시 전체 루프 중단
                        if len(article_ids) >= 15:
                            break
                        
                        if article_ids:
                            logger.info(f"선택자 '{selector}'에서 총 {len(article_ids)}개 게시글 수집 완료")
                            break
                        
                except Exception as e:
                    logger.debug(f"선택자 {selector} 실패: {e}")
                    continue
            
            # 만약 기존 선택자로 찾지 못했다면, 더 일반적인 방법으로 시도
            if not article_ids:
                logger.info("기존 선택자 실패, 더 일반적인 방법으로 시도")
                try:
                    # 모든 테이블 확인
                    tables = self.driver.find_elements(By.TAG_NAME, "table")
                    logger.info(f"총 {len(tables)}개 테이블 발견")
                    
                    for table_idx, table in enumerate(tables):
                        table_class = table.get_attribute('class')
                        logger.info(f"테이블 {table_idx}: class='{table_class}'")
                        
                        if 'article' in table_class:
                            # 이 테이블의 모든 tr 확인
                            trs = table.find_elements(By.TAG_NAME, "tr")
                            logger.info(f"게시글 테이블에서 {len(trs)}개 tr 발견")
                            
                            for i, tr in enumerate(trs):
                                try:
                                    # tr 안의 모든 링크 확인
                                    links = tr.find_elements(By.TAG_NAME, "a")
                                    for link in links:
                                        href = link.get_attribute('href')
                                        if href and '/articles/' in href and f"menuid={self.menu_id}" in href:
                                            match = re.search(r'/articles/(\d+)', href)
                                            if match:
                                                article_id = int(match.group(1))
                                                title = link.text.strip()
                                                article_ids.append(article_id)
                                                logger.info(f"테이블 tr {i}에서 게시글 발견: ID={article_id}, 제목={title[:50]}...")
                                                break
                                except Exception as e:
                                    logger.debug(f"테이블 tr {i} 처리 실패: {e}")
                                    continue
                    
                except Exception as e:
                    logger.warning(f"일반적인 방법 실패: {e}")
            
            # iframe에서도 찾지 못했으면 메인 페이지에서 다시 시도
            if not article_ids and iframe_switched:
                logger.info("iframe에서 찾지 못함, 메인 페이지로 돌아가서 재시도")
                self.driver.switch_to.default_content()
                time.sleep(3)
                
                # 메인 페이지에서 다시 시도
                try:
                    # 페이지 소스 확인
                    page_source = self.driver.page_source
                    if 'class="article"' in page_source:
                        logger.info("메인 페이지에 class='article' 태그 존재")
                        
                        # 메인 페이지에서 선택자 재시도
                        for selector in ["a.article", "a[class='article']", "a[href*='/articles/']"]:
                            try:
                                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                logger.info(f"메인 페이지 선택자 '{selector}': {len(elements)}개 링크 발견")
                                
                                for elem in elements:
                                    try:
                                        href = elem.get_attribute('href')
                                        if href and '/articles/' in href:
                                            match = re.search(r'/articles/(\d+)', href)
                                            if match:
                                                article_id = int(match.group(1))
                                                article_ids.append(article_id)
                                                title = elem.text.strip()[:50] or "제목없음"
                                                logger.info(f"메인 페이지에서 게시글 발견: ID={article_id}, 제목={title}")
                                    except:
                                        continue
                                
                                if article_ids:
                                    break
                                    
                            except Exception as e:
                                logger.debug(f"메인 페이지 선택자 {selector} 실패: {e}")
                                continue
                    else:
                        logger.warning("메인 페이지에도 게시글이 없습니다")
                        
                except Exception as e:
                    logger.warning(f"메인 페이지 재시도 실패: {e}")
            else:
                # 기본 frame으로 돌아가기
                if iframe_switched:
                    self.driver.switch_to.default_content()
            
            # 중복 제거
            article_ids = list(set(article_ids))
            logger.info(f"페이지 {page}에서 {len(article_ids)}개 게시글 ID 수집")
            
            return sorted(article_ids, reverse=True)
            
        except Exception as e:
            logger.error(f"게시글 목록 가져오기 실패 (페이지 {page}): {e}")
            return []
    
    def get_article_detail(self, article_id):
        """게시글 상세 정보 가져오기 (사용자 제공 URL 형식 사용)"""
        try:
            # 사용자 제공 실제 URL 형식: https://cafe.naver.com/pnpsecure2/7241
            article_url = f"https://cafe.naver.com/{self.cafe_name}/{article_id}"
            logger.info(f"게시글 상세 접근: {article_url}")
            
            self.driver.get(article_url)
            self.random_delay(5, 8)
            
            # 페이지 완전 로딩 대기
            WebDriverWait(self.driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # iframe 전환
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.frame_to_be_available_and_switch_to_it((By.NAME, "cafe_main"))
                )
                logger.info("게시글 페이지 cafe_main iframe 전환 성공")
            except:
                try:
                    iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                    if iframes:
                        self.driver.switch_to.frame(iframes[0])
                        logger.info("게시글 페이지 첫 번째 iframe 전환")
                except:
                    logger.warning("iframe 전환 실패")
            
            # 게시글 데이터 초기화
            article_data = {
                'id': article_id,
                'title': '제목 없음',
                'content': '내용 없음',
                'comments': '댓글 없음',
                'url': f"https://cafe.naver.com/{self.cafe_name}/{article_id}"
            }
            
            # XPath 또는 CSS 선택자로 데이터 추출 시도
            self.extract_article_data(article_data)
            
            # 댓글 수집
            comments = self.get_comments()
            if comments:
                # 댓글들을 문자열로 합치기 (작성자: 내용 형식)
                comment_strings = []
                for comment in comments:
                    comment_str = f"{comment['author']}: {comment['content']}"
                    comment_strings.append(comment_str)
                article_data['comments'] = " | ".join(comment_strings)
                logger.info(f"댓글 {len(comments)}개 수집 완료")
            
            # 기본 frame으로 돌아가기
            self.driver.switch_to.default_content()
            
            return article_data
            
        except Exception as e:
            logger.error(f"게시글 {article_id} 상세 정보 가져오기 실패: {e}")
            return None
    
    def extract_article_data(self, article_data):
        """게시글 데이터 추출 (사용자 제공 HTML 구조 기반)"""
        
        # 제목 추출 - 사용자 제공: <h3 class="title_text">
        try:
            title_element = self.driver.find_element(By.CSS_SELECTOR, "h3.title_text")
            title = title_element.text.strip()
            if title:
                article_data['title'] = title
                logger.info(f"제목 발견: {title}")
        except Exception as e:
            logger.warning(f"제목 추출 실패: {e}")
            # 대안 선택자들
            title_selectors = [
                "h3.title_text",
                "h2.tit", 
                ".article-title", 
                ".subject", 
                "h1", 
                "h2", 
                ".title",
                ".ArticleTitle",
                ".article_title"
            ]
            for selector in title_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    title = element.text.strip()
                    if title and len(title) > 1:
                        article_data['title'] = title
                        logger.info(f"제목 발견 (대안 선택자 {selector}): {title[:50]}...")
                        break
                except:
                    continue
        
        # 내용 추출 - se-main-container 클래스를 우선적으로 시도
        content_found = False
        try:
            # se-main-container 클래스에서 내용 추출 (최우선)
            content_element = self.driver.find_element(By.CSS_SELECTOR, "div.se-main-container")
            content_text = content_element.text.strip()
            
            if content_text:
                # 빈 줄만 제거하고 모든 내용 포함
                lines = [line.strip() for line in content_text.split('\n') if line.strip()]
                article_data['content'] = '\n'.join(lines)
                logger.info(f"내용 발견 (se-main-container): {content_text[:100]}...")
                content_found = True
            else:
                logger.warning("se-main-container에서 내용이 비어있음")
                
        except Exception as e:
            logger.warning(f"se-main-container 실패: {e}")
        
        # se-main-container에서 실패한 경우 기존 경로들 시도
        if not content_found:
            try:
                # ContentRenderer 하위의 첫 번째 div 태그 선택
                content_element = self.driver.find_element(By.CSS_SELECTOR, "div.ContentRenderer > div:first-child")
                content_text = content_element.text.strip()
                
                if content_text:
                    # 빈 줄만 제거하고 모든 내용 포함
                    lines = [line.strip() for line in content_text.split('\n') if line.strip()]
                    article_data['content'] = '\n'.join(lines)
                    logger.info(f"내용 발견 (ContentRenderer > div:first-child): {content_text[:100]}...")
                    content_found = True
                else:
                    article_data['content'] = "내용 없음"
                    
            except Exception as e:
                logger.warning(f"ContentRenderer > div:first-child 실패: {e}")
                # 대안으로 ContentRenderer 전체 시도
                try:
                    content_element = self.driver.find_element(By.CSS_SELECTOR, "div.ContentRenderer")
                    content_text = content_element.text.strip()
                    
                    if content_text:
                        lines = [line.strip() for line in content_text.split('\n') if line.strip()]
                        article_data['content'] = '\n'.join(lines)
                        logger.info(f"내용 발견 (ContentRenderer 전체): {content_text[:100]}...")
                        content_found = True
                    else:
                        article_data['content'] = "내용 없음"
                        
                except Exception as e2:
                    logger.warning(f"ContentRenderer도 실패: {e2}")
                    article_data['content'] = "내용 없음"
        
        # 내용이 여전히 없으면 ArticleContentBox > article_container > 첫번째 div에서 시도
        if not content_found or article_data['content'] == "내용 없음":
            try:
                logger.info("대안 경로 시도: ArticleContentBox > article_container > 첫번째 div")
                # ArticleContentBox 클래스 > article_container 클래스 하위의 첫번째 div 태그
                content_element = self.driver.find_element(By.CSS_SELECTOR, "div.ArticleContentBox div.article_container > div:first-child")
                content_text = content_element.text.strip()
                
                if content_text:
                    lines = [line.strip() for line in content_text.split('\n') if line.strip()]
                    article_data['content'] = '\n'.join(lines)
                    logger.info(f"내용 발견 (ArticleContentBox > article_container > div:first-child): {content_text[:100]}...")
                    content_found = True
                else:
                    logger.warning("ArticleContentBox 경로에서도 내용이 비어있음")
                    
            except Exception as e3:
                logger.warning(f"ArticleContentBox 경로도 실패: {e3}")
                # 최종 대안으로 article_container 전체 시도
                try:
                    content_element = self.driver.find_element(By.CSS_SELECTOR, "div.ArticleContentBox div.article_container")
                    content_text = content_element.text.strip()
                    
                    if content_text:
                        lines = [line.strip() for line in content_text.split('\n') if line.strip()]
                        article_data['content'] = '\n'.join(lines)
                        logger.info(f"내용 발견 (article_container 전체): {content_text[:100]}...")
                        content_found = True
                    else:
                        logger.warning("article_container 전체에서도 내용이 비어있음")
                        
                except Exception as e4:
                    logger.warning(f"모든 내용 추출 방법 실패: {e4}")
                    if article_data['content'] == "내용 없음":
                        article_data['content'] = "내용을 찾을 수 없습니다"
    
    def get_comments(self):
        """댓글 수집 - CommentBox 클래스 > 2번째 div 태그 > ul 태그 기반"""
        comments = []
        
        try:
            # CommentBox 클래스 > 2번째 div 태그 > ul 태그 찾기
            comment_box = self.driver.find_element(By.CSS_SELECTOR, "div.CommentBox")
            logger.info("CommentBox 클래스 발견")
            
            # 2번째 div 태그 찾기
            div_elements = comment_box.find_elements(By.CSS_SELECTOR, "> div")
            if len(div_elements) >= 2:
                second_div = div_elements[1]  # 2번째 div (인덱스 1)
                logger.info("CommentBox 내 2번째 div 태그 발견")
                
                # ul 태그 찾기
                ul_elements = second_div.find_elements(By.TAG_NAME, "ul")
                if ul_elements:
                    ul_element = ul_elements[0]  # 첫 번째 ul 태그
                    logger.info("2번째 div 내 ul 태그 발견")
                    
                    # ul 내의 모든 li 요소 (각 댓글)
                    li_elements = ul_element.find_elements(By.TAG_NAME, "li")
                    logger.info(f"총 {len(li_elements)}개 댓글 li 요소 발견")
                    
                    for i, li in enumerate(li_elements[:20]):  # 최대 20개 댓글
                        try:
                            comment_data = {
                                'author': '댓글작성자 없음',
                                'content': '댓글내용 없음',
                                'date': '댓글날짜 없음'
                            }
                            
                            # 댓글 작성자 찾기
                            try:
                                author_elem = li.find_element(By.CSS_SELECTOR, "a.comment_nickname, .nickname, .author")
                                comment_data['author'] = author_elem.text.strip()
                            except:
                                # 대안으로 li 내의 모든 a 태그 확인
                                try:
                                    a_elements = li.find_elements(By.TAG_NAME, "a")
                                    for a in a_elements:
                                        if a.text.strip() and len(a.text.strip()) > 0:
                                            comment_data['author'] = a.text.strip()
                                            break
                                except:
                                    pass
                            
                            # 댓글 내용 찾기
                            try:
                                content_elem = li.find_element(By.CSS_SELECTOR, "span.text_comment, .comment_text_view, .comment_text_box")
                                comment_data['content'] = content_elem.text.strip()[:500]
                            except:
                                # 대안으로 li의 텍스트에서 작성자명 제거
                                try:
                                    li_text = li.text.strip()
                                    if comment_data['author'] != '댓글작성자 없음' and comment_data['author'] in li_text:
                                        content_text = li_text.replace(comment_data['author'], '', 1).strip()
                                        if content_text:
                                            comment_data['content'] = content_text[:500]
                                except:
                                    pass
                            
                            # 댓글 날짜 찾기
                            try:
                                date_elem = li.find_element(By.CSS_SELECTOR, "span.comment_info_date, .date, .comment_date")
                                comment_data['date'] = date_elem.text.strip()
                            except:
                                pass
                            
                            # 유효한 댓글인 경우만 추가
                            if comment_data['content'] != '댓글내용 없음' and len(comment_data['content']) > 1:
                                comments.append(comment_data)
                                logger.info(f"댓글 {i+1}: {comment_data['author']} - {comment_data['content'][:50]}...")
                            
                        except Exception as e:
                            logger.warning(f"댓글 li {i+1} 처리 실패: {e}")
                            continue
                else:
                    logger.warning("2번째 div 내에 ul 태그를 찾을 수 없음")
            else:
                logger.warning(f"CommentBox 내에 2번째 div가 없음 (총 {len(div_elements)}개 div 발견)")
                
        except Exception as e:
            logger.warning(f"CommentBox 기반 댓글 수집 실패: {e}")
            # 기존 방식으로 폴백
            try:
                logger.info("기존 댓글 수집 방식으로 폴백 시도")
                comment_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.comment_box")
                logger.info(f"기존 방식으로 {len(comment_elements)}개 댓글 발견")
                
                for i, elem in enumerate(comment_elements[:20]):
                    try:
                        comment_data = {
                            'author': '댓글작성자 없음',
                            'content': '댓글내용 없음',
                            'date': '댓글날짜 없음'
                        }
                        
                        # 댓글 작성자
                        try:
                            author_elem = elem.find_element(By.CSS_SELECTOR, "a.comment_nickname")
                            comment_data['author'] = author_elem.text.strip()
                        except:
                            try:
                                author_elem = elem.find_element(By.CSS_SELECTOR, ".comment_nick_info a, .nickname")
                                comment_data['author'] = author_elem.text.strip()
                            except:
                                pass
                        
                        # 댓글 내용
                        try:
                            content_elem = elem.find_element(By.CSS_SELECTOR, "span.text_comment")
                            comment_data['content'] = content_elem.text.strip()[:500]
                        except:
                            try:
                                content_elem = elem.find_element(By.CSS_SELECTOR, ".comment_text_view, .comment_text_box")
                                comment_data['content'] = content_elem.text.strip()[:500]
                            except:
                                pass
                        
                        # 댓글 날짜
                        try:
                            date_elem = elem.find_element(By.CSS_SELECTOR, "span.comment_info_date")
                            comment_data['date'] = date_elem.text.strip()
                        except:
                            try:
                                date_elem = elem.find_element(By.CSS_SELECTOR, ".comment_info_box .comment_info_date")
                                comment_data['date'] = date_elem.text.strip()
                            except:
                                pass
                        
                        if comment_data['content'] != '댓글내용 없음':
                            comments.append(comment_data)
                            logger.info(f"폴백 댓글 {i+1}: {comment_data['author']} - {comment_data['content'][:50]}...")
                            
                    except Exception as e2:
                        logger.warning(f"폴백 댓글 {i+1} 처리 실패: {e2}")
                        continue
                        
            except Exception as e2:
                logger.error(f"폴백 댓글 수집도 실패: {e2}")
        
        return comments
    
    def save_article_to_csv(self, article_data, filename="cafe_articles_mgr_3page.csv", is_first=False):
        """게시글 데이터를 CSV 파일에 실시간으로 저장"""
        try:
            # CSV 파일에 추가 (첫 번째 게시글인 경우 헤더 포함)
            mode = "w" if is_first else "a"
            with open(filename, mode, newline='', encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                
                # 첫 번째 게시글인 경우 헤더 작성
                if is_first:
                    writer.writerow(["게시글ID", "제목", "내용", "댓글", "URL"])
                
                # 게시글 데이터 작성
                writer.writerow([
                    article_data.get('id', ''),
                    article_data.get('title', ''),
                    article_data.get('content', ''),
                    article_data.get('comments', ''),
                    article_data.get('url', '')
                ])
            
            logger.info(f"💾 CSV 저장 완료: 게시글 {article_data.get('id')} - {article_data.get('title', '')[:30]}...")
            return True
            
        except Exception as e:
            logger.error(f"CSV 저장 실패: {e}")
            return False
    
    def crawl_cafe(self):
        """메인 크롤링 함수 (페이지별 즉시 스크랩)"""
        try:
            # 드라이버 설정
            self.setup_driver()
            
            # 네이버 로그인
            if not self.naver_login():
                logger.error("로그인 실패로 크롤링 중단")
                return []
            
            # 페이지별로 게시글을 바로 스크랩
            all_articles = []
            max_pages = 3  # 최대 6페이지까지
            successful_count = 0
            total_processed = 0
            
            logger.info(f"=== 페이지별 즉시 스크랩 시작 (최대 {max_pages}페이지) ===")
            logger.info(f"📋 예상 수집량: 1페이지(~18개) + 2-6페이지(~15개씩) = 최대 {self.max_articles}개")
            
            for page in range(3, max_pages + 1): # 3 페이지 아티클만 크롤링

                expected_count = 18 if page == 1 else 15
                logger.info(f"📄 {page}페이지 처리 시작... (예상: ~{expected_count}개)")
                
                # 현재 페이지의 게시글 ID 목록 가져오기
                article_ids = self.get_article_list(page)
                
                if not article_ids:
                    logger.warning(f"페이지 {page}에서 게시글을 찾을 수 없어 다음 페이지로 이동")
                    continue
                
                actual_count = len(article_ids)
                if page == 1 and actual_count > 15:
                    logger.info(f"📋 {page}페이지에서 {actual_count}개 게시글 발견 (공지사항 포함), 즉시 스크랩 시작")
                else:
                    logger.info(f"📋 {page}페이지에서 {actual_count}개 게시글 발견, 즉시 스크랩 시작")
                
                # 현재 페이지의 게시글들을 바로 스크랩
                for i, article_id in enumerate(article_ids):
                    try:
                        total_processed += 1
                        
                        # 최대 게시글 수 제한 확인
                        if total_processed > self.max_articles:
                            logger.info(f"🛑 최대 게시글 수({self.max_articles}개) 도달, 크롤링 종료")
                            return all_articles
                        
                        logger.info(f"[{page}페이지 {i+1}/{actual_count}] 전체 진행률: {total_processed}/{self.max_articles} - 게시글 ID: {article_id}")
                        
                        article_data = self.get_article_detail(article_id)
                        if article_data:
                            all_articles.append(article_data)
                            
                            # 실시간으로 CSV에 저장 (첫 번째 게시글인 경우 헤더 포함)
                            is_first_article = (successful_count == 0)
                            if self.save_article_to_csv(article_data, is_first=is_first_article):
                                successful_count += 1
                                logger.info(f"✅ [{page}페이지] 게시글 {article_id} 수집 및 저장 완료 - 총 {successful_count}개 저장됨")
                            else:
                                logger.warning(f"⚠️ [{page}페이지] 게시글 {article_id} 수집은 완료되었지만 CSV 저장 실패")
                        else:
                            logger.warning(f"❌ [{page}페이지] 게시글 {article_id} 수집 실패")
                        
                        # 요청 간격 조절
                        self.random_delay(3, 6)
                        
                    except Exception as e:
                        logger.error(f"[{page}페이지] 게시글 {article_id} 처리 중 오류: {e}")
                        continue
                
                logger.info(f"📋 {page}페이지 처리 완료 ({actual_count}개 중 처리)")
                
                # 페이지 간 대기
                self.random_delay(2, 4)
            
            logger.info(f"🎉 모든 페이지 크롤링 완료! 총 {successful_count}개 게시글이 CSV에 저장되었습니다.")
            return all_articles
            
        except Exception as e:
            logger.error(f"크롤링 중 오류: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()

def main():
    logger.info("=== 2025년 버전 네이버 카페 크롤링 시작 (페이지별 즉시 스크랩) ===")
    
    crawler = NaverCafeCrawler()
    articles = crawler.crawl_cafe()
    
    if articles:
        # 수집 결과 요약
        logger.info(f"📊 최종 수집 결과 요약:")
        logger.info(f"   - 총 게시글: {len(articles)}개")
        logger.info(f"   - 저장된 파일: cafe_articles_mgr_3page.csv")
    else:
        logger.error("❌ 게시글 수집 실패")

if __name__ == "__main__":
    main() 