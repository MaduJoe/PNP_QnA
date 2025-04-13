
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

## 추가 기능

- **크롤링 스크립트**: `scripts/crawl_cafe.py`를 통해 네이버 카페의 FAQ 데이터를 수집하여 학습 데이터로 활용 가능
- **MantisBT API 연동**: OpenAPI 규격(openapi.yaml)을 통해 이슈 추적 시스템과 연동

## 아키텍처

```
                  ┌─────────────┐
                  │  LINE 메신저  │
                  └──────┬──────┘
                         │
                         ▼
┌────────────────────────────────────────┐
│            Flask 웹 서버                │
│      (BugSearchBot 클래스 실행)         │
└─────────────┬─────────────┬────────────┘
              │             │
              ▼             ▼
┌────────────────┐  ┌─────────────────┐
│   OpenAI API   │  │    MantisBT API  │
└────────────────┘  └─────────────────┘
```

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.

## 개발자

- MaduJoe - 초기 개발 