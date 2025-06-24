import time
import yaml
import logging
from linebot.v3 import WebhookHandler
from flask import Flask, request, abort
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from concurrent.futures import ThreadPoolExecutor
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent, PostbackEvent
from linebot.v3.messaging import (
    TemplateMessage, CarouselTemplate, CarouselColumn, PostbackAction, PushMessageRequest
)
from hybrid_search import HybridSearchEngine

# 로깅 설정
logging.basicConfig(level=logging.INFO)

class BugSearchBot:
    def __init__(self, config_file="config.yaml"):
        """라인봇 초기화"""
        with open(config_file, "r", encoding="utf-8") as file:
            self.config = yaml.safe_load(file)

        # 라인봇 설정
        self.line_access_token = self.config["line_bot"]["access_token"]
        self.line_channel_secret = self.config["line_bot"]["channel_secret"]
        self.flask_debug = self.config["app"]["debug"]
        self.flask_port = self.config["app"]["port"]
        
        # Flask 앱 및 라인봇 핸들러 설정
        self.app = Flask(__name__)
        self.configuration = Configuration(access_token=self.line_access_token)
        self.handler = WebhookHandler(self.line_channel_secret)
        
        # 하이브리드 검색 엔진 초기화
        self.search_engine = HybridSearchEngine(config_file)
        self.search_engine_initialized = False
        
        # 사용자 상태 관리
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

    def initialize_search_engine(self):
        """검색 엔진 초기화 (백그라운드에서 실행)"""
        if not self.search_engine_initialized:
            try:
                logging.info("🔥 하이브리드 검색 엔진 초기화 시작...")
                self.search_engine.initialize()
                self.search_engine_initialized = True
                logging.info("✅ 하이브리드 검색 엔진 초기화 완료!")
            except Exception as e:
                logging.error(f"검색 엔진 초기화 실패: {e}")
                raise

    def callback(self):
        """라인봇 콜백 처리"""
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
        user_id = event.source.user_id
        data = event.postback.data
        reply_token = event.reply_token

        # 사용자의 선택에 따라 상태 설정
        if "action=bugs_qna" in data:
            self.user_states[user_id] = "bugs_qna"
            reply_text = "🐛 Bugs QnA를 선택하셨습니다.\n🔍 키워드와 의미 검색을 모두 활용합니다!\n검색하고 싶은 키워드나 문제를 입력해 주세요."
        elif "action=product_qna" in data:
            self.user_states[user_id] = "product_qna"
            reply_text = "💻 Product QnA를 선택하셨습니다.\n🔍 키워드와 의미 검색을 모두 활용합니다!\n검색하고 싶은 키워드나 문제를 입력해 주세요."
        else:
            reply_text = "알 수 없는 선택입니다."

        # 응답 메시지 전송
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=reply_text)],
                )
            )

    def handle_message(self, event, destination):
        """사용자 메시지 처리"""
        user_id = event.source.user_id
        keyword = event.message.text.strip()

        # 사용자 상태 확인
        service_type = self.user_states.get(user_id)
        if not service_type:
            # 상태가 설정되지 않은 경우, Carousel Template 전송
            self.send_carousel_template(event.reply_token)
            return

        try:
            # 검색 엔진이 초기화되지 않은 경우
            if not self.search_engine_initialized:
                with ApiClient(self.configuration) as api_client:
                    line_bot_api = MessagingApi(api_client)
                    line_bot_api.reply_message_with_http_info(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text="🔧 하이브리드 검색 시스템을 초기화하고 있습니다.\n잠시 후 다시 시도해 주세요.")],
                        )
                    )
                return

            # 즉시 응답 메시지 전송
            with ApiClient(self.configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="🔍 하이브리드 검색 중입니다...\n(키워드 + 의미 검색)\n잠시만 기다려 주세요.")],
                    )
                )

            # 백그라운드에서 검색 수행
            def process_search():
                try:
                    # 하이브리드 유사도 검색 수행
                    results = self.search_engine.hybrid_search(keyword)
                    
                    # 결과 포맷팅
                    if results:
                        response_text = self.format_search_results(results, keyword, service_type)
                    else:
                        response_text = f"'{keyword}'에 대한 검색 결과를 찾을 수 없습니다.\n다른 키워드로 다시 시도해 보세요."

                    # 검색 결과 전송
                    with ApiClient(self.configuration) as api_client:
                        line_bot_api = MessagingApi(api_client)
                        push_request = PushMessageRequest(
                            to=user_id,
                            messages=[TextMessage(text=response_text)]
                        )
                        line_bot_api.push_message_with_http_info(push_request)
                        
                except Exception as e:
                    logging.error(f"검색 처리 중 오류 발생: {e}", exc_info=True)
                    # 에러 메시지 전송
                    with ApiClient(self.configuration) as api_client:
                        line_bot_api = MessagingApi(api_client)
                        push_request = PushMessageRequest(
                            to=user_id,
                            messages=[TextMessage(text="죄송합니다. 검색 중 오류가 발생했습니다. 다시 시도해 주세요.")]
                        )
                        line_bot_api.push_message_with_http_info(push_request)

            # 스레드 풀에서 검색 실행
            executor = ThreadPoolExecutor(max_workers=5)
            executor.submit(process_search)

        except Exception as e:
            logging.error(f"메시지 처리 중 오류 발생: {e}", exc_info=True)

    def format_search_results(self, results, keyword, service_type):
        """검색 결과를 라인봇 형식으로 포맷팅"""
        emoji = "🐛" if service_type == "bugs_qna" else "💻"
        
        response = f"{emoji} '{keyword}' 하이브리드 검색 결과\n"
        response += "🔍 키워드 + 의미 검색 결합\n\n"
        
        for i, result in enumerate(results, 1):
            response += f"📌 {i}. {result['title']}\n"
            response += f"📂 카테고리: {result['category']}\n"
            response += f"🎯 종합점수: {result['combined_score']:.3f}\n"
            
            # 키워드 매칭 여부 표시
            if result['keyword_score'] > 0:
                response += f"✅ 키워드 매칭됨\n"
            else:
                response += f"🧠 의미적 유사성\n"
            
            response += f"🔗 {result['url']}\n\n"
        
        response += "💡 더 정확한 키워드를 사용하면 더 좋은 결과를 얻을 수 있습니다!"
        return response

    def send_carousel_template(self, reply_token):
        """Carousel Template 전송"""
        carousel_template = CarouselTemplate(
            columns=[
                CarouselColumn(
                    thumbnail_image_url="https://raw.githubusercontent.com/MaduJoe/PNP_QnA/refs/heads/main/mantis.jpg",
                    title="🐛 Bugs QnA",
                    text="이슈 및 버그 관련 문의에 대한 하이브리드 AI 검색 서비스입니다.",
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
                    title="💻 PC Assist Conf QnA",
                    text="제품 관련 문의에 대한 하이브리드 AI 검색 서비스입니다.",
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
                    messages=[TemplateMessage(alt_text="하이브리드 QnA 서비스 선택", template=carousel_template)],
                )
            )

    def handle_follow(self, event):
        """사용자가 챗봇을 친구로 추가하거나 대화방에 들어올 때 Carousel Template 제공"""
        reply_token = event.reply_token
        welcome_message = "🎉 PNP QnA Bot에 오신 것을 환영합니다!\n\n🔥 새로운 하이브리드 검색 시스템:\n• 🔤 키워드 검색 + 🧠 의미 검색 결합\n• 더 정확하고 신뢰할 수 있는 결과\n\n아래에서 원하는 서비스를 선택해 주세요:"
        
        # 환영 메시지 전송
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=welcome_message)],
                )
            )
        
        # 잠시 후 Carousel Template 전송
        time.sleep(1)
        self.send_carousel_template(reply_token)

    def run(self):
        """Flask 앱 실행"""
        # 백그라운드에서 검색 엔진 초기화
        init_executor = ThreadPoolExecutor(max_workers=1)
        init_executor.submit(self.initialize_search_engine)
        
        logging.info(f"🚀 하이브리드 검색 라인봇 서버 시작 (포트: {self.flask_port})")
        self.app.run(debug=self.flask_debug, port=self.flask_port, host='0.0.0.0')

if __name__ == "__main__":
    bot = BugSearchBot(config_file="config.yaml")
    bot.run() 