from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# 크롬 드라이버 경로 설정 (환경에 따라 변경)
# driver_path = r'C:/chromedriver-win64/chromedriver.exe'

chrome_driver_path = "C:/chromedriver-win64/chromedriver.exe"  # 또는 Windows: "C:\\chromedriver.exe"

# Chrome Service 객체 생성
service = Service(executable_path=chrome_driver_path)

# 드라이버 실행
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=service, options=options)

# 네이버 로그인 페이지 접속
driver.get("https://nid.naver.com/nidlogin.login")
time.sleep(2)

# 로그인 정보 입력 (보안을 위해 ID/PW는 직접 입력 권장)
naver_id = "pnp_jkcho"
naver_pw = "100djrqjsek!"

# ID/PW 입력
driver.find_element(By.ID, "id").send_keys(naver_id)
driver.find_element(By.ID, "pw").send_keys(naver_pw)
driver.find_element(By.ID, "log.login").click()
time.sleep(3)

# 카페 게시판으로 이동
cafe_board_url = "https://cafe.naver.com/29308153/64"  # 예시: https://cafe.naver.com/example/123
driver.get(cafe_board_url)
time.sleep(3)

# 카페는 iframe으로 구성되어 있음 → 프레임 전환
driver.switch_to.frame("cafe_main")
time.sleep(2)

# 게시글 제목 수집
titles = driver.find_elements(By.CSS_SELECTOR, ".article-board .article")  # 최신 UI용
for t in titles:
    try:
        title = t.find_element(By.CSS_SELECTOR, ".article .board-list .td_article").text
        print(title)
    except:
        continue

# 종료
driver.quit()
