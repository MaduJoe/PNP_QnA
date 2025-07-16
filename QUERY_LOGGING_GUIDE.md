# PNP QnA Bot 질의 로깅 시스템 사용 가이드

## 개요

PNP QnA Bot에 사용자 질의를 자동으로 저장하고 관리할 수 있는 로깅 시스템이 추가되었습니다. 
이 시스템을 통해 사용자들의 질의 패턴을 분석하고, 자주 묻는 질문을 파악할 수 있습니다.

## 주요 기능

- ✅ **자동 질의 저장**: 모든 사용자 질의와 검색 결과를 자동으로 SQLite 데이터베이스에 저장
- ✅ **응답 시간 측정**: 각 질의의 처리 시간을 밀리초 단위로 기록
- ✅ **카테고리별 결과 추적**: Product QnA와 Bugs QnA 각각의 결과 수를 분리하여 저장
- ✅ **통계 분석**: 기간별 질의 통계 및 인기 키워드 분석
- ✅ **실시간 모니터링**: 실시간으로 들어오는 질의를 모니터링
- ✅ **CSV 내보내기**: 분석을 위한 데이터 내보내기 기능

## 설정 방법

### 1. config.yaml 설정

`config.yaml` 파일에 다음 설정이 추가되어 있습니다:

```yaml
# 질의 로깅 설정
query_logging:
  enabled: true                              # 질의 로깅 활성화 여부
  db_path: "./query_logs.db"                # SQLite 데이터베이스 파일 경로
  log_results: true                          # 검색 결과도 함께 저장할지 여부
  log_response_time: true                    # 응답 시간 로깅 여부
```

### 2. 로깅 비활성화

로깅을 중단하려면 `enabled: false`로 설정하세요:

```yaml
query_logging:
  enabled: false
```

## 질의 관리 도구 사용법

`query_manager.py` 스크립트를 사용하여 저장된 질의를 조회하고 관리할 수 있습니다.

### 기본 사용법

```bash
# 가상환경 활성화
source .qna_env/bin/activate

# 최근 질의 20개 조회
python3 query_manager.py recent

# 최근 질의 50개 조회
python3 query_manager.py recent --limit 50

# 키워드로 질의 검색
python3 query_manager.py search "로그인"

# 특정 질의 상세 조회 (ID: 123)
python3 query_manager.py detail 123

# 최근 7일 통계 조회
python3 query_manager.py stats

# 최근 30일 통계 조회
python3 query_manager.py stats --days 30

# CSV로 내보내기 (최근 30일)
python3 query_manager.py export queries_30days.csv

# 실시간 모니터링
python3 query_manager.py monitor
```

### 출력 예시

#### 1. 최근 질의 조회
```
최근 질의 20개 (총 15개)
================================================================================
ID    사용자ID         질의내용                        시간                 P/B/T    응답시간  
================================================================================
15    Ud54c6a2c9...   인사연동 모듈 미동작              2025-07-16 11:53:38  2/1/3    1250ms   
14    Ud54c6a2c9...   pnp_api                       2025-07-16 11:49:52  1/2/3    890ms    
13    Ud54c6a2c9...   매니저 로그인 문제               2025-07-16 10:25:11  3/0/3    1150ms   
```

#### 2. 통계 조회
```
📊 질의 통계 (최근 7일)
================================================================================
총 질의 수: 156개
고유 사용자 수: 23명
평균 결과 수: 4.2개/질의
평균 응답 시간: 1,250.5ms

🔥 인기 질의 (TOP 10):
   1. 로그인 오류 (12회)
   2. 인사연동 (8회)
   3. 매니저 접속 (7회)
   4. 권한 설정 (6회)
   5. API 연동 (5회)
```

#### 3. 질의 상세 조회
```
질의 상세 정보 (ID: 15)
================================================================================
사용자 ID: Ud54c6a2c9170dc1e9362f9f2764a5626
질의 내용: 인사연동 모듈 미동작
질의 시간: 2025-07-16 11:53:38
응답 시간: 1250.50ms
Product QnA 결과 수: 2
Bugs QnA 결과 수: 1
총 결과 수: 3

💻 Product QnA 결과:
  1. 인사연동 설정 방법
     카테고리: Manager, 점수: 0.892
     URL: https://cafe.naver.com/pnpsecure2/7241

🐛 Bugs QnA 결과:
  1. 인사연동 모듈 오류 수정
     카테고리: Bugs, 점수: 0.845
     URL: https://bugs.pnpsecure.com/view.php?id=28456
```

## 데이터베이스 구조

SQLite 데이터베이스의 `query_logs` 테이블 구조:

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | INTEGER | 기본키 (자동증가) |
| user_id | TEXT | 라인봇 사용자 ID |
| query_text | TEXT | 사용자 질의 내용 |
| timestamp | DATETIME | 질의 시간 |
| product_results_count | INTEGER | Product QnA 결과 수 |
| bugs_results_count | INTEGER | Bugs QnA 결과 수 |
| total_results_count | INTEGER | 총 결과 수 |
| product_results_json | TEXT | Product QnA 결과 (JSON) |
| bugs_results_json | TEXT | Bugs QnA 결과 (JSON) |
| response_time_ms | REAL | 응답 시간 (밀리초) |
| created_at | DATETIME | 레코드 생성 시간 |

## 데이터 분석 활용

### 1. Excel/Google Sheets에서 분석
```bash
# CSV로 내보내기
python3 query_manager.py export analysis_data.csv --days 30
```

내보낸 CSV 파일을 Excel이나 Google Sheets에서 열어 다음과 같은 분석이 가능합니다:
- 시간대별 질의 패턴
- 사용자별 질의 빈도
- 검색 결과가 없는 질의 식별
- 응답 시간 분석

### 2. Python으로 고급 분석
```python
import pandas as pd
import sqlite3

# 데이터베이스 연결
conn = sqlite3.connect('query_logs.db')

# 일별 질의 수 조회
daily_queries = pd.read_sql_query("""
    SELECT DATE(timestamp) as date, COUNT(*) as query_count
    FROM query_logs 
    GROUP BY DATE(timestamp)
    ORDER BY date
""", conn)

# 결과가 없는 질의 찾기
no_results = pd.read_sql_query("""
    SELECT query_text, COUNT(*) as count
    FROM query_logs 
    WHERE total_results_count = 0
    GROUP BY query_text
    ORDER BY count DESC
""", conn)
```

## 주의사항

1. **개인정보 보호**: 사용자 ID는 라인봇에서 제공하는 암호화된 ID이므로 개인 식별이 불가능합니다.
2. **저장 공간**: 시간이 지나면서 데이터베이스 크기가 증가할 수 있으니 주기적으로 정리하세요.
3. **백업**: 중요한 분석 데이터이므로 정기적으로 백업하세요.

## 문제해결

### 질의 로깅이 작동하지 않는 경우
1. `config.yaml`에서 `query_logging.enabled: true` 확인
2. SQLite 데이터베이스 파일 쓰기 권한 확인
3. 로그에서 오류 메시지 확인

### 데이터베이스 파일이 없는 경우
시스템이 자동으로 생성하므로 별도 작업이 필요하지 않습니다.

## 추가 기능 요청

추가로 필요한 기능이 있다면 다음과 같은 것들을 고려해볼 수 있습니다:
- 웹 대시보드 구현
- 자동 보고서 생성
- 알림 기능 (특정 키워드 감지 시)
- 더 고급 통계 분석

---

📞 **문의사항**이 있으시면 언제든지 말씀해 주세요! 