import time
import yaml
import logging
from openai import OpenAI
from linebot.v3 import WebhookHandler
from flask import Flask, request, abort
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from concurrent.futures import ThreadPoolExecutor
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent, PostbackEvent
from linebot.v3.messaging import (
    TemplateMessage, CarouselTemplate, CarouselColumn, PostbackAction, PushMessageRequest
)

# logging.basicConfig(level=logging.DEBUG)

# OpenAIClient 클래스
class OpenAIClient:
    def __init__(self, api_key, assistant_id):
        self.api_key = api_key 
        self.assistant_id = assistant_id
        self.client = OpenAI(api_key=self.api_key)
        self.thread_id = self.client.beta.threads.create().id

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
        self.bugs_id = self.config["openai"]["bugs_id"]
        self.assistant_id = self.config["openai"]["assistant_id"]
        self.flask_debug = self.config["app"]["debug"]
        self.flask_port = self.config["app"]["port"]
        self.mantis_api_url = self.config['mantis_api']['url']
        self.mantis_api_key = self.config['mantis_api']['api_key']
        self.app = Flask(__name__)
        self.configuration = Configuration(access_token=self.line_access_token)
        self.handler = WebhookHandler(self.line_channel_secret)
        self.openai_client = None
        self.user_states = {}

        # 라우트 및 핸들러 등록
        self.app.add_url_rule(
            "/callback", "callback", lambda: self.callback(), methods=["POST"]
        )
        self.handler.add(MessageEvent, message=TextMessageContent)(
            lambda event, destination: self.handle_message(event, destination)
        )
        self.handler.add(FollowEvent)(lambda event: self.handle_follow(event))
        self.handler.add(PostbackEvent)(lambda event: self.handle_postback(event))

    def callback(self):
        signature = request.headers["X-Line-Signature"]
        body = request.get_data(as_text=True)
        self.app.logger.info("Request body: " + body)
        try:
            self.handler.handle(body, signature)
        except InvalidSignatureError:
            abort(400)
        return "OK"

    def handle_postback(self, event):
        """사용자가 Carousel Template 버튼을 클릭했을 때의 이벤트 처리"""
        user_id = event.source.user_id  # 사용자 ID
        data = event.postback.data      # Postback 데이터
        reply_token = event.reply_token

        # 사용자의 선택에 따라 상태 설정
        if "action=bugs_qna" in data:
            self.user_states[user_id] = "bugs_qna"  # 사용자 상태 설정
            self.openai_client = OpenAIClient(
                self.OPENAI_API_KEY, self.bugs_id
            )
            reply_text = "Bugs QnA를 선택하셨습니다. 키워드를 입력해 주세요."
        elif "action=product_qna" in data:
            self.user_states[user_id] = "product_qna"  # 사용자 상태 설정
            self.openai_client = OpenAIClient(
                self.OPENAI_API_KEY, self.assistant_id
            )
            reply_text = "Product QnA를 선택하셨습니다. 키워드를 입력해 주세요."
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

    def handle_message(self, event, destination):
        user_id = event.source.user_id
        keyword = event.message.text.strip()

        # 사용자 상태 확인
        service_type = self.user_states.get(user_id)
        if not service_type:
            # 상태가 설정되지 않은 경우, Carousel Template 전송
            self.send_carousel_template(event.reply_token)
            return

        try:
            with ApiClient(self.configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="답변을 생성중 입니다. 잠시만 기다려 주세요.")],
                    )
                )

            def process_response():
                try:
                    if service_type == "bugs_qna":
                        response_text = self.openai_client.ask(f"Bugs QnA 키워드: {keyword}")
                    elif service_type == "product_qna":
                        response_text = self.openai_client.ask(f"Product QnA 키워드: {keyword}")
                    else:
                        response_text = "알 수 없는 서비스 타입입니다."

                    with ApiClient(self.configuration) as api_client:
                        line_bot_api = MessagingApi(api_client)
                        push_request = PushMessageRequest(
                            to=user_id,
                            messages=[TextMessage(text=response_text)]
                        )
                        line_bot_api.push_message_with_http_info(push_request)
                except Exception as e:
                    logging.error(f"Error in process_response: {e}", exc_info=True)

            executor = ThreadPoolExecutor(max_workers=12)
            executor.submit(process_response)

        except Exception as e:
            logging.error(f"Error in handle_message: {e}", exc_info=True)

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

    def handle_follow(self, event):
        """사용자가 챗봇을 친구로 추가하거나 대화방에 들어올 때 Carousel Template 제공"""
        reply_token = event.reply_token
        self.send_carousel_template(reply_token)

    def run(self):
        self.app.run(debug=self.flask_debug, port=self.flask_port)

if __name__ == "__main__":
    bot = BugSearchBot(config_file="config.yaml")
    bot.run()
