# 🤖 PNP QnA Bot - 로컬 GPU 임베딩 시스템

## 📋 개요

기존 OpenAI API 기반 QnA 봇을 로컬 GPU 서버를 활용한 임베딩 기반 유사도 검색 시스템으로 업그레이드했습니다.

### 🔄 변경사항

**이전 (OpenAI API 기반):**
1. 사용자 질문 입력
2. OpenAI Assistant API 호출
3. 생성된 답변 응답

**현재 (로컬 GPU 임베딩 기반):**
1. 사용자 질문 입력
2. 게시글(제목+내용+댓글) 임베딩과 질문 임베딩 계산
3. 코사인 유사도 계산
4. 유사도 Top 3 추출 → URL 응답

## 🛠️ 시스템 구성

### 핵심 컴포넌트

1. **EmbeddingSearchEngine** (`embedding_search.py`)
   - 한국어 임베딩 모델 (`jhgan/ko-sroberta-multitask`)
   - 게시글 데이터 로딩 및 전처리
   - 임베딩 계산 및 캐싱
   - 코사인 유사도 검색

2. **BugSearchBot** (`pnp_qna_bot_embedding.py`)
   - 라인봇 인터페이스
   - 비동기 검색 처리
   - 결과 포맷팅 및 응답

3. **데이터 소스**
   - `scripts/cafe_articles_dbs.csv`: DBS 관련 게시글
   - `scripts/cafe_articles_mgr.csv`: Manager 관련 게시글

## 🚀 설치 및 실행

### 1. 환경 설정

```bash
# 가상환경 생성 (권장)
python -m venv .qna_env
source .qna_env/bin/activate  # Windows: .qna_env\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 설정 파일 확인

`config.yaml`에서 다음 설정들을 확인/수정:

```yaml
# 로컬 임베딩 시스템 설정
embedding:
  model_name: "jhgan/ko-sroberta-multitask"  # 한국어 임베딩 모델
  cache_dir: "./embeddings_cache"            # 임베딩 캐시 저장 경로
  batch_size: 32                             # 배치 크기
  max_length: 512                            # 최대 토큰 길이
  top_k: 3                                   # 반환할 상위 결과 수

# 데이터 설정
data:
  articles_path: "./scripts/"                # 게시글 데이터 경로
  dbs_file: "cafe_articles_dbs.csv"         # DBS 게시글 파일
  mgr_file: "cafe_articles_mgr.csv"         # Manager 게시글 파일
```

### 3. 시스템 테스트

```bash
# 임베딩 검색 시스템 테스트
python test_embedding_search.py
```

### 4. 라인봇 서버 실행

```bash
# 새로운 임베딩 기반 라인봇 실행
python pnp_qna_bot_embedding.py
```

## 🔧 GPU 활용

### CUDA 사용 설정

시스템에서 CUDA가 사용 가능한 경우 자동으로 GPU를 활용합니다:

```python
# 자동 GPU 감지 및 사용
device = "cuda" if torch.cuda.is_available() else "cpu"
```

### GPU 메모리 최적화

대량의 게시글 처리를 위한 배치 처리:

```python
# 배치 단위로 임베딩 계산
batch_size = 32  # GPU 메모리에 따라 조정
```

## 📊 성능 특징

### 장점
1. **오프라인 동작**: 인터넷 연결 없이 로컬에서 실행
2. **비용 절감**: OpenAI API 비용 없음
3. **빠른 응답**: 사전 계산된 임베딩 활용
4. **확장성**: 게시글 추가 시 캐시 업데이트만 필요
5. **정확성**: 실제 게시글 데이터 기반 검색

### 주요 기능
- **캐싱 시스템**: 계산된 임베딩을 파일로 저장
- **배치 처리**: GPU 메모리 효율적 사용
- **유사도 계산**: 코사인 유사도 기반 정확한 매칭
- **다국어 지원**: 한국어 특화 임베딩 모델

## 📁 파일 구조

```
QnA-BoT/
├── config.yaml                    # 설정 파일
├── embedding_search.py            # 임베딩 검색 엔진
├── pnp_qna_bot_embedding.py      # 새로운 라인봇 (임베딩 기반)
├── pnp_qna_bot.py                 # 기존 라인봇 (OpenAI 기반)
├── test_embedding_search.py       # 테스트 스크립트
├── requirements.txt               # 패키지 의존성
├── embeddings_cache/              # 임베딩 캐시 디렉토리
└── scripts/
    ├── cafe_articles_dbs.csv      # DBS 게시글 데이터
    └── cafe_articles_mgr.csv      # Manager 게시글 데이터
```

## 🔍 사용 방법

### 라인봇 인터페이스

1. **서비스 선택**
   - 🐛 Bugs QnA: 이슈/버그 관련 검색
   - 💻 Product QnA: 제품 관련 검색

2. **검색 쿼리**
   - 자연어 질문 가능
   - 키워드 검색 지원
   - 예: "매니저 로그인 문제", "DBSAFER 설치 오류"

3. **결과 응답**
   - Top 3 유사 게시글
   - 제목, 카테고리, 유사도 점수
   - 원본 게시글 URL 링크

### 직접 API 사용

```python
from embedding_search import EmbeddingSearchEngine

# 검색 엔진 초기화
search_engine = EmbeddingSearchEngine()
search_engine.initialize()

# 검색 수행
results = search_engine.search_similar_articles("매니저 로그인 오류")

# 결과 출력
for result in results:
    print(f"제목: {result['title']}")
    print(f"유사도: {result['similarity']:.3f}")
    print(f"URL: {result['url']}")
```

## 🛡️ 트러블슈팅

### 일반적인 문제

1. **GPU 메모리 부족**
   ```yaml
   # config.yaml에서 배치 크기 조정
   embedding:
     batch_size: 16  # 기본값 32에서 줄임
   ```

2. **모델 다운로드 실패**
   ```bash
   # 수동으로 모델 다운로드
   python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('jhgan/ko-sroberta-multitask')"
   ```

3. **캐시 파일 오류**
   ```bash
   # 캐시 디렉토리 삭제 후 재생성
   rm -rf embeddings_cache/
   ```

## 🔄 기존 시스템과 비교

| 항목 | 기존 (OpenAI API) | 새로운 (로컬 임베딩) |
|------|------------------|-------------------|
| 비용 | API 호출 비용 발생 | 무료 (하드웨어 비용만) |
| 응답 시간 | 네트워크 의존적 | 로컬 처리로 빠름 |
| 정확성 | 생성형 AI 답변 | 실제 게시글 기반 |
| 오프라인 | 불가능 | 가능 |
| 확장성 | API 제한 | 하드웨어 제한 |
| 유지보수 | API 변경 영향 | 로컬 제어 가능 |

## 📈 향후 개선 사항

1. **실시간 데이터 업데이트**: 새로운 게시글 자동 추가
2. **하이브리드 검색**: 키워드 + 임베딩 결합
3. **사용자 피드백**: 검색 결과 품질 개선
4. **다중 모델**: 다양한 임베딩 모델 지원
5. **API 서버**: REST API 인터페이스 제공

---

🎯 **이제 OpenAI API 없이도 고품질의 QnA 서비스를 로컬 GPU로 제공할 수 있습니다!** 