# PNP QnA Bot

LINE 메신저 기반 질의응답 봇으로, OpenAI API와 연동하여 두 가지 유형의 질문에 답변할 수 있는 서비스입니다.

## 기능 소개

- **Bugs QnA**: 이슈 관리 시스템(MantisBT)의 데이터를 활용하여 이슈 문의에 대한 답변을 제공
- **Product QnA**: 제품 관련 질문에 대한 정보를 제공
- LINE 메신저 인터페이스를 통한 사용자 친화적 경험
- OpenAI Assistant API를 활용한 자연어 처리 및 응답 생성

## 주요 컴포넌트

### 1. OpenAIClient 클래스
- OpenAI Assistant API와 통신하는 클라이언트
- Thread 관리, 메시지 제출, 응답 획득 등의 기능 제공

### 2. BugSearchBot 클래스
- LINE 메신저와 OpenAI API 사이의 통합 관리
- 사용자 상호작용 처리 및 응답 생성
- Carousel UI를 통한 서비스 선택 기능

## 기술 스택

- **프로그래밍 언어**: Python
- **웹 프레임워크**: Flask
- **메신저 플랫폼**: LINE
- **AI 서비스**: OpenAI (Assistant API)
- **이슈 추적 시스템**: MantisBT

## 설치 및 실행 방법

### 필수 요구사항
- Python 3.8 이상
- LINE Bot API 계정 및 설정
- OpenAI API 키

### 설치 단계
1. 저장소 클론
   ```bash
   git clone https://github.com/MaduJoe/PNP_QnA.git
   cd PNP_QnA
   ```

2. 필요한 패키지 설치
   ```bash
   pip install -r requirements.txt
   ```

3. config.yaml 파일 설정
   ```yaml
   line_bot:
     access_token: "YOUR_LINE_ACCESS_TOKEN"
     channel_secret: "YOUR_LINE_CHANNEL_SECRET"
   openai:
     api_key: "YOUR_OPENAI_API_KEY"
     bugs_id: "YOUR_BUGS_ASSISTANT_ID"
     assistant_id: "YOUR_PRODUCT_ASSISTANT_ID"
   app:
     debug: false
     port: 5000
   mantis_api:
     url: "YOUR_MANTIS_API_URL"
     api_key: "YOUR_MANTIS_API_KEY"
   ```

4. 실행
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