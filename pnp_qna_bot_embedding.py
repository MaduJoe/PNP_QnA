import yaml
import logging
import time
from linebot.v3 import WebhookHandler
from flask import Flask, request, abort
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage, PushMessageRequest
from concurrent.futures import ThreadPoolExecutor
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent
from hybrid_search import HybridSearchEngine
from query_logger import QueryLogger


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
        
        # 질의 로거 초기화
        self.query_logging_config = self.config.get("query_logging", {})
        if self.query_logging_config.get("enabled", False):
            db_path = self.query_logging_config.get("db_path", "./query_logs.db")
            self.query_logger = QueryLogger(db_path)
            logging.info("질의 로깅 시스템 활성화됨")
        else:
            self.query_logger = None
            logging.info("질의 로깅 시스템 비활성화됨")

        # 라우트 및 핸들러 등록
        self.app.add_url_rule(
            "/callback", "callback", lambda: self.callback(), methods=["POST"]
        )
        self.handler.add(MessageEvent, message=TextMessageContent)(
            lambda event, destination: self.handle_message(event, destination)
        )
        self.handler.add(FollowEvent)(lambda event: self.handle_follow(event))

    def initialize_search_engine(self):
        """검색 엔진 초기화 (백그라운드에서 실행)"""
        if not self.search_engine_initialized:
            try:
                logging.info("하이브리드 검색 엔진 초기화 시작...")
                self.search_engine.initialize()
                self.search_engine_initialized = True
                logging.info("하이브리드 검색 엔진 초기화 완료!")
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



    def handle_message(self, event, destination):
        """사용자 메시지 처리 - 통합 검색 방식"""
        user_id = event.source.user_id
        keyword = event.message.text.strip()

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
                        messages=[TextMessage(text="🔍 카테고리별 하이브리드 검색 중입니다...\n💻 Product QnA (카페) & 🐛 Bugs QnA (버그추적)\n잠시만 기다려 주세요.")],
                    )
                )

            # 백그라운드에서 검색 수행
            def process_search():
                search_start_time = time.time()
                try:
                    # 카테고리별 하이브리드 검색 수행
                    config = self.search_engine.embedding_config
                    product_top_k = config.get("product_top_k", 3)
                    bugs_top_k = config.get("bugs_top_k", 3)
                    
                    category_results = self.search_engine.hybrid_search_by_category(
                        keyword, 
                        product_top_k=product_top_k, 
                        bugs_top_k=bugs_top_k
                    )
                    
                    # 응답 시간 계산
                    response_time_ms = (time.time() - search_start_time) * 1000
                    
                    # 결과 포맷팅 - 카테고리별 분리 응답
                    if category_results["product_qna"] or category_results["bugs_qna"]:
                        response_text = self.format_category_search_results(category_results, keyword)
                    else:
                        response_text = f"'{keyword}'에 대한 검색 결과를 찾을 수 없습니다.\n다른 키워드로 다시 시도해 보세요."
                    
                    # 질의 로깅 (설정이 활성화된 경우)
                    if self.query_logger and self.query_logging_config.get("log_results", True):
                        try:
                            log_response_time = response_time_ms if self.query_logging_config.get("log_response_time", True) else None
                            self.query_logger.log_query(
                                user_id=user_id,
                                query_text=keyword,
                                category_results=category_results,
                                response_time_ms=log_response_time
                            )
                        except Exception as log_error:
                            logging.error(f"질의 로깅 실패: {log_error}")

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

    def format_unified_search_results(self, results, keyword):
        """통합 검색 결과를 라인봇 형식으로 포맷팅"""
        response = f"🔍 '{keyword}' 통합 하이브리드 검색 결과\n"
        response += "🐛💻 Bugs & Product QnA 동시 검색\n"
        response += "🔍 키워드 + 의미 검색 결합\n\n"
        
        for i, result in enumerate(results, 1):
            # URL에 따른 이모지 설정
            if "bugs.pnpsecure.com" in result['url']:
                category_emoji = "🐛"
                service_label = "[Bugs QnA]"
            else:  # cafe.naver.com URL
                category_emoji = "💻"
                service_label = "[Product QnA]"
            
            response += f"📌 {i}. {service_label} {result['title']}\n"
            response += f"📂 카테고리: {category_emoji} {result['category']}\n"
            response += f"🎯 종합점수: {result['combined_score']:.3f}\n"
            
            # 키워드 매칭 여부 표시
            if result.get('keyword_score', 0) > 0:
                response += f"✅ 키워드 매칭됨\n"
            else:
                response += f"🧠 의미적 유사성\n"
            
            response += f"🔗 {result['url']}\n\n"
        
        response += "💡 클릭 없이 Bugs와 Product 문의 결과를 동시에 확인하세요!\n"
        response += "🎯 더 정확한 키워드를 사용하면 더 좋은 결과를 얻을 수 있습니다!"
        return response

    def format_category_search_results(self, category_results, keyword):
        """카테고리별 분리 검색 결과를 라인봇 형식으로 포맷팅"""
        response = f"🔍 '{keyword}' 카테고리별 하이브리드 검색 결과\n"
        response += "🔍 키워드 + 의미 검색 결합\n\n"
        
        # Product QnA 결과
        product_results = category_results["product_qna"]
        if product_results:
            response += "=" * 27 + "\n"
            response += "💻 **Product QnA 결과**\n"
            response += "=" * 27 + "\n"
            for i, result in enumerate(product_results, 1):
                response += f"📌 {i}. [Product QnA] {result['title']}\n"
                response += f"📂 카테고리: 💻 {result['category']}\n"
                response += f"🎯 종합점수: {result['combined_score']:.3f}\n"
                
                # 키워드 매칭 여부 표시
                if result.get('keyword_score', 0) > 0:
                    response += f"✅ 키워드 매칭됨\n"
                else:
                    response += f"🧠 의미적 유사성\n"
                
                response += f"🔗 {result['url']}\n\n"
        else:
            response += "=" * 27 + "\n"
            response += "💻 **Product QnA 결과**\n"
            response += "=" * 27 + "\n"
            response += "❌ Product QnA에서 관련 결과를 찾을 수 없습니다.\n\n"
        
        # Bugs QnA 결과
        bugs_results = category_results["bugs_qna"]
        if bugs_results:
            response += "=" * 27 + "\n"
            response += "🐛 **Bugs QnA 결과**\n"
            response += "=" * 27 + "\n"
            for i, result in enumerate(bugs_results, 1):
                response += f"📌 {i}. [Bugs QnA] {result['title']}\n"
                response += f"📂 카테고리: 🐛 {result['category']}\n"
                response += f"🎯 종합점수: {result['combined_score']:.3f}\n"
                
                # 키워드 매칭 여부 표시
                if result.get('keyword_score', 0) > 0:
                    response += f"✅ 키워드 매칭됨\n"
                else:
                    response += f"🧠 의미적 유사성\n"
                
                response += f"🔗 {result['url']}\n\n"
        else:
            response += "=" * 27 + "\n"
            response += "🐛 **Bugs QnA 결과**\n"
            response += "=" * 27 + "\n"
            response += "❌ Bugs QnA에서 관련 결과를 찾을 수 없습니다.\n\n"
        
        response += "💡 이제 Product QnA(카페)와 Bugs QnA(버그추적) 결과를 각각 확인할 수 있습니다!\n"
        response += "🎯 더 정확한 키워드를 사용하면 더 좋은 결과를 얻을 수 있습니다!"
        return response

    def handle_follow(self, event):
        """사용자가 챗봇을 친구로 추가하거나 대화방에 들어올 때 환영 메시지 제공"""
        reply_token = event.reply_token
        welcome_message = "🎉 PNP QnA Bot에 오신 것을 환영합니다!\n\n🔥 통합 검색 시스템:\n• 🔤 키워드 검색 + 🧠 의미 검색 결합\n• 💻 Product QnA (카페) & 🐛 Bugs QnA (버그추적) 분리 검색\n\n💡 검색하고 싶은 키워드나 문제를 바로 입력해 주세요!"
        
        # 환영 메시지 전송
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=welcome_message)],
                )
            )

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
