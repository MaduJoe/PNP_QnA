import re
import time
import yaml
import logging
import requests
from openai import OpenAI
from linebot.v3 import WebhookHandler
from flask import Flask, request, abort
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from concurrent.futures import ThreadPoolExecutor, as_completed
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent, PostbackEvent  # PostbackEvent 추가
from linebot.v3.messaging import (
    TemplateMessage, CarouselTemplate, CarouselColumn, PostbackAction, PushMessageRequest
)
# from linebot.v3.messaging.models import (
#     RichMenuRequest, RichMenuSize, RichMenuBounds, RichMenuArea, PostbackAction
# )

logging.basicConfig(level=logging.DEBUG)

# OpenAIClient 클래스
class OpenAIClient:
    def __init__(self, api_key, assistant_id, thread_id):
        self.api_key = api_key
        self.assistant_id = assistant_id
        self.client = OpenAI(api_key=self.api_key)
        self.thread_id = self.client.beta.threads.create().id
        print(f"self.thread_id : {self.thread_id}")

    def wait_on_run(self, run):
        while run.status == "queued" or run.status == "in_progress":
            run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread_id, run_id=run.id
            )
            time.sleep(0.5)
        return run

    def submit_message(self, user_message):
        self.client.beta.threads.messages.create(
            thread_id=self.thread_id, role="user", content=user_message
        )
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread_id, assistant_id=self.assistant_id
        )
        return run

    def get_response(self):
        return self.client.beta.threads.messages.list(
            thread_id=self.thread_id, order="asc"
        )

    def ask(self, user_message):
        run = self.submit_message(user_message)
        self.wait_on_run(run)
        response = self.get_response()
        return response.data[-1].content[0].text.value  # 마지막 Assistant 메시지 반환
    
class BugSearchBot:
    def __init__(self, config_file="config.yaml"):
        with open(config_file, "r") as file:
            self.config = yaml.safe_load(file)

        self.line_access_token = self.config["line_bot"]["access_token"]
        self.line_channel_secret = self.config["line_bot"]["channel_secret"]
        self.OPENAI_API_KEY = self.config["openai"]["api_key"]
        self.assistant_id = self.config["openai"]["assistant_id"]
        self.thread_id = self.config["openai"]["thread_id"]
        self.flask_debug = self.config["app"]["debug"]
        self.flask_port = self.config["app"]["port"]
        self.mantis_api_url = self.config['mantis_api']['url']
        self.mantis_api_key = self.config['mantis_api']['api_key']
        self.app = Flask(__name__)
        self.configuration = Configuration(access_token=self.line_access_token)
        self.handler = WebhookHandler(self.line_channel_secret)

        self.openai_client = OpenAIClient(
            self.OPENAI_API_KEY, self.assistant_id, self.thread_id
        )
        self.user_states = {}

        # 라우트 및 핸들러 등록
        self.app.add_url_rule(
            "/callback", "callback", lambda: self.callback(), methods=["POST"]
        )
        self.handler.add(MessageEvent, message=TextMessageContent)(
            lambda event, destination: self.handle_message(event, destination)
        )

        # 라우트 및 핸들러 등록
        self.handler.add(FollowEvent)(lambda event: self.handle_follow(event))
        self.handler.add(PostbackEvent)(lambda event: self.handle_postback(event))  # PostbackEvent 등록
            
    def fetch_issues_with_keyword(self, keyword):
        headers = {
            "Authorization": f"{self.mantis_api_key}",
            "Content-Type": "application/json"
        }

        def fetch_page(page):
            params = {"page_size": 100, "page": page}
            response = requests.get(self.mantis_api_url, headers=headers, params=params)
            if response.status_code == 200:
                return response.json().get("issues", [])
            else:
                print(f"Failed to fetch page {page}. Status code: {response.status_code}")
                return []

        # 키워드를 공백으로 분리하고 각 단어에 가중치 부여
        keyword_parts = keyword.split()
        keyword_weights = {part: weight for part, weight in zip(keyword_parts, range(len(keyword_parts), 0, -1))}
        keyword_patterns = {re.compile(re.escape(part), re.IGNORECASE): weight for part, weight in keyword_weights.items()}

        all_issues = []

        # 병렬로 페이지 요청
        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = {executor.submit(fetch_page, page): page for page in range(1, 55)}
            for future in as_completed(futures):
                issues = future.result()
                print(f"Fetched page {futures[future]} with {len(issues)} issues.")

                for issue in issues:
                    summary = issue.get("summary", "")
                    description = issue.get("description", "")

                    # 매칭된 단어와 가중치 계산
                    matched_keywords = set()
                    total_weight = 0

                    for pattern, weight in keyword_patterns.items():
                        if pattern.search(summary) or pattern.search(description):
                            matched_keywords.add(pattern.pattern)
                            total_weight += weight

                    # 적어도 2개의 단어가 매칭되었는지 확인
                    # if len(matched_keywords) >= 2:
                    all_issues.append({
                        "id": issue["id"],
                        "summary": summary,
                        "description": description or "No description available.",
                        "matched_keywords": list(matched_keywords),
                        "total_weight": total_weight
                    })

        # 빈 데이터 처리
        if not all_issues:
            print("No issues found in the API response.")
            reply_text = "No issues found with the given keyword."
            return reply_text
 
        # total_weight 기준으로 내림차순 정렬 후 상위 5개 선택
        sorted_issues = sorted(all_issues, key=lambda x: x["total_weight"], reverse=True)[:5]

        # 응답 메시지 생성
        reply_text = "Found issues:\n"
        for issue in sorted_issues:  # 정렬된 상위 5개의 이슈만 표시
            issue_link = f"https://bugs.pnpsecure.com/view.php?id={issue['id']}"
            reply_text += (
                f"ID: {issue['id']}\n"
                f"Link: {issue_link}\n"
                f"Summary: {issue['summary']}\n"
                f"Matched Keywords: {', '.join(issue['matched_keywords'])}\n"
                f"Total Weight: {issue['total_weight']}\n\n"
            )

        return reply_text

    def callback(self):
        signature = request.headers["X-Line-Signature"]
        body = request.get_data(as_text=True)
        self.app.logger.info("Request body: " + body)
        try:
            self.handler.handle(body, signature)
        except InvalidSignatureError:
            abort(400)
        return "OK"

    def send_carousel_template(self, reply_token):
        """Carousel Template 전송"""
        carousel_template = CarouselTemplate(
            columns=[
                CarouselColumn(
                    thumbnail_image_url="https://raw.githubusercontent.com/MaduJoe/PNP_QnA/refs/heads/main/mantis.jpg",
                    title="Bugs QnA",
                    text="이슈 문의에 대한 답변을 도와주는 생성형 AI입니다",
                    actions=[
                        PostbackAction(
                            label="Bugs 문의하기",
                            data="action=bugs_qna",
                            display_text="Bugs QnA를 선택했습니다.",
                        )
                    ]
                ),
                CarouselColumn(
                    thumbnail_image_url="https://raw.githubusercontent.com/MaduJoe/PNP_QnA/refs/heads/main/pcassist.jpg",
                    title="PC Assist Conf QnA",
                    text="제품 문의에 대한 답변을 도와주는 생성형 AI입니다.",
                    actions=[ 
                        PostbackAction(
                            label="Product 문의하기",
                            data="action=product_qna",
                            display_text="Product QnA를 선택했습니다.",
                        ) 
                    ]
                )
            ] 
        )
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TemplateMessage(alt_text="Choose QnA Service", template=carousel_template)],
                )
            )

    def handle_postback(self, event):
        """사용자가 Carousel Template 버튼을 클릭했을 때의 이벤트 처리"""
        user_id = event.source.user_id  # 사용자 ID
        data = event.postback.data      # Postback 데이터
        reply_token = event.reply_token

        # 사용자의 선택에 따라 상태 설정
        if "action=bugs_qna" in data:
            self.user_states[user_id] = "bugs_qna"  # 사용자 상태 설정
            reply_text = "Bugs QnA를 선택하셨습니다. 키워드를 입력해 주세요."
            logging.debug(f"[DEBUG] User {user_id} 상태 설정: bugs_qna")
        elif "action=product_qna" in data:
            self.user_states[user_id] = "product_qna"  # 사용자 상태 설정
            reply_text = "Product QnA를 선택하셨습니다. 키워드를 입력해 주세요."
            logging.debug(f"[DEBUG] User {user_id} 상태 설정: product_qna")
        else:
            reply_text = "알 수 없는 선택입니다."

        # 키워드 입력 안내 메시지 전송
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=reply_text)],
                )
            )
            
    def handle_follow(self, event):
        """사용자가 챗봇을 친구로 추가하거나 대화방에 들어올 때 Carousel Template 제공"""
        reply_token = event.reply_token
        self.send_carousel_template(reply_token)

    def handle_message(self, event, destination):
        user_id = event.source.user_id
        keyword = event.message.text.strip()

        # 사용자 상태 확인
        service_type = self.user_states.get(user_id)
        
        if not service_type:
            # 상태가 설정되지 않은 경우, Carousel Template 전송
            self.send_carousel_template(event.reply_token)  # 리치메뉴누르면 이함수 호출 > 카드나오는 이유 
            return

        try:
            # 응답 생성 중 메시지 전송
            with ApiClient(self.configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="답변을 생성중 입니다. 잠시만 기다려 주세요.")],
                    )
                ) 
             
            # 비동기로 최종 응답 생성 및 전송
            def process_response():
                try:
                    if service_type == "bugs_qna":
                        response_text = self.fetch_issues_with_keyword(keyword)
                    elif service_type == "product_qna":
                        response_text = self.openai_client.ask(f"Product QnA 키워드: {keyword}")
                    else:
                        response_text = "알 수 없는 서비스 타입입니다."

                    # 최종 응답은 Push Message로 전송
                    with ApiClient(self.configuration) as api_client:
                        line_bot_api = MessagingApi(api_client)
                        push_request = PushMessageRequest(
                            to=user_id,
                            messages=[TextMessage(text=response_text)]
                        )
                        line_bot_api.push_message_with_http_info(push_request)
                    logging.debug(f"Final response sent to user {user_id}.")
                except Exception as e:
                    logging.error(f"Error in process_response: {e}", exc_info=True)
            
            # 비동기 작업 실행
            executor = ThreadPoolExecutor(max_workers=12)
            executor.submit(process_response)
        
        except Exception as e:
            logging.error(f"Error in handle_message: {e}", exc_info=True)
        
    def run(self):
        """Flask 앱 실행"""
        self.app.run(debug=self.flask_debug, port=self.flask_port)


if __name__ == "__main__":
    bot = BugSearchBot(config_file="config.yaml")
    bot.run()
