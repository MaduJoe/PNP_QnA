
# 🧠 PNP QnA Bot

PNP QnA Bot은 사내 이슈 관리 시스템(MantisBT)과 제품 관련 QnA를 통합하여 **LINE 메시징 플랫폼을 통해 자연어 기반 질의 응답**을 제공하는 **AI 챗봇 시스템**입니다.  
OpenAI API를 활용해 키워드 기반의 요약 및 답변 생성을 수행하며, 사용자의 선택에 따라 두 가지 서비스 타입을 지원합니다:  
- **Bugs QnA**: 버그/이슈에 대한 질의
- **Product QnA**: 제품 문서 기반의 질의

## 📌 주요 기능

| 기능 | 설명 |
|------|------|
| 🔍 키워드 기반 이슈 검색 | LINE 메시지로 키워드를 입력하면 관련 이슈를 자동으로 검색 |
| 💬 OpenAI 기반 요약 응답 | 검색된 이슈 또는 문서 내용을 요약하여 자연어 응답 생성 |
| 🔗 LINE 챗봇 인터페이스 | Carousel Template을 활용한 UI/UX 및 선택형 QnA 흐름 구성 |
| 🔐 MantisBT API 연동 | OpenAPI 기반의 프록시 API를 통해 이슈 정보를 가져옴 |
| ⚙️ 비동기 응답 처리 | ThreadPoolExecutor로 대화 흐름 비차단 처리 |

## 🧱 아키텍처

```plaintext
[User - LINE App]
      │
      ▼
[LINE Bot (Webhook)]
      │
      ├── Carousel Template으로 QnA 타입 선택
      │
      └─▶ Flask 백엔드 서버
              │
              ├── MantisBT Proxy API 요청 (이슈 검색)
              ├── OpenAI Assistant 호출 (답변 생성)
              └── 결과를 LINE 메시지로 푸시 전송
```

- **MantisBT Proxy API**: `/issues/{issue_id}` 경로로 특정 이슈 데이터를 가져오는 OpenAPI 명세 기반 REST API
- **OpenAI API**: Assistants API를 통해 메시지 스레드 단위 생성형 응답
- **LINE Messaging API**: 메시지 수신 및 응답 (reply, push)

## 🛠 사용 기술

| 범주 | 기술 스택 |
|------|-----------|
| Backend | Python, Flask |
| Messaging API | LINE Messaging API v3 |
| AI | OpenAI Assistants API (threads/messages/runs) |
| DevOps | Ngrok (로컬 터널링) |
| API 스펙 | OpenAPI 3.0 (Swagger 기반 문서화) |
| 기타 | YAML 설정 파일 관리, ThreadPoolExecutor (비동기 처리) |

## 🔧 실행 방법

1. **환경 구성**
```bash
pip install -r requirements.txt
```

2. **`config.yaml` 구성**
```yaml
line_bot:
  access_token: "YOUR_LINE_ACCESS_TOKEN"
  channel_secret: "YOUR_LINE_CHANNEL_SECRET"

openai:
  api_key: "YOUR_OPENAI_API_KEY"
  assistant_id: "ASSISTANT_ID_PRODUCT_QNA"
  bugs_id: "ASSISTANT_ID_BUGS_QNA"

app:
  debug: true
  port: 5000

mantis_api:
  url: "https://your-ngrok-url/api/rest/index.php"
  api_key: "YOUR_MANTIS_API_KEY"
```

3. **서버 실행**
```bash
python pnp_qna_bot.py
```

4. **Ngrok 터널링**
```bash
ngrok http 5000
```

5. **LINE Webhook 설정**
- [LINE Developers Console](https://developers.line.biz/console/)에서 채널 생성
- Webhook URL에 `https://<your-ngrok>.ngrok.io/callback` 입력

## 🧪 예시 흐름

1. 사용자가 챗봇에게 메시지를 보냄
2. 챗봇이 Carousel로 "Bugs QnA" 또는 "Product QnA"를 선택하도록 유도
3. 사용자가 키워드 입력 → OpenAI가 요약 응답 생성
4. 응답은 LINE 메시지로 푸시됨

## 📂 프로젝트 구조

```bash
PNP_QnA/
├── pnp_qna_bot.py            # 메인 Flask 애플리케이션 및 LINE 핸들러
├── config.yaml               # 환경 설정 파일 (비공개 필요)
├── openapi.yaml              # MantisBT API 명세
├── static/                   # 이미지 파일 (Carousel에 사용)
└── README.md                 # 프로젝트 설명 문서
```

## 👨‍💻 개발팀

- **팀명**: QA Ninjas  
- **역할 분담**:  
  - 챗봇/AI 연동: 조재근
  - 시스템 구조 설계: 조재근  
  - 발표/문서화: 조재근/김하림

## 📎 참고 자료

- [LINE Messaging API 공식문서](https://developers.line.biz/en/docs/messaging-api/overview)
- [OpenAI Assistants API](https://platform.openai.com/playground/assistants)
- [Toss Payments 용어사전(Webhook 등)](https://docs.tosspayments.com/resources/glossary/webhook)
