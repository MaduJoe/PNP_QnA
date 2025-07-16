#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Query Logger - 사용자 질의 로깅 및 관리 시스템
SQLite를 사용하여 간단하고 효율적으로 질의 내역을 저장/관리
"""

import sqlite3
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import os

# 한국 시간대 설정 (UTC+9)
KST = timezone(timedelta(hours=9))

class QueryLogger:
    """사용자 질의 로깅 및 관리 클래스"""
    
    def __init__(self, db_path: str = "query_logs.db"):
        """
        질의 로거 초기화
        
        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """데이터베이스 및 테이블 초기화"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 질의 로그 테이블 생성
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS query_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        query_text TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        product_results_count INTEGER DEFAULT 0,
                        bugs_results_count INTEGER DEFAULT 0,
                        total_results_count INTEGER DEFAULT 0,
                        product_results_json TEXT,
                        bugs_results_json TEXT,
                        response_time_ms REAL,
                        created_at DATETIME NOT NULL
                    )
                ''')
                
                # 통계용 인덱스 생성
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON query_logs(timestamp)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_user_id 
                    ON query_logs(user_id)
                ''')
                
                conn.commit()
                self.logger.info(f"질의 로그 데이터베이스 초기화 완료: {self.db_path}")
                
        except Exception as e:
            self.logger.error(f"데이터베이스 초기화 실패: {e}")
            raise
    
    def log_query(self, 
                  user_id: str, 
                  query_text: str, 
                  category_results: Dict[str, List[Dict]], 
                  response_time_ms: Optional[float] = None) -> int:
        """
        사용자 질의 로깅
        
        Args:
            user_id: 사용자 ID
            query_text: 질의 텍스트
            category_results: 카테고리별 검색 결과
            response_time_ms: 응답 시간 (밀리초)
            
        Returns:
            int: 생성된 로그 ID
        """
        try:
            product_results = category_results.get("product_qna", [])
            bugs_results = category_results.get("bugs_qna", [])
            
            # JSON으로 변환 (URL과 주요 정보만 저장)
            product_json = json.dumps([
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "category": r.get("category", ""),
                    "combined_score": r.get("combined_score", 0)
                } for r in product_results
            ], ensure_ascii=False)
            
            bugs_json = json.dumps([
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "category": r.get("category", ""),
                    "combined_score": r.get("combined_score", 0)
                } for r in bugs_results
            ], ensure_ascii=False)
            
            # 한국 시간으로 현재 시간 생성
            kst_now = datetime.now(KST)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO query_logs 
                    (user_id, query_text, timestamp, created_at, product_results_count, bugs_results_count, 
                     total_results_count, product_results_json, bugs_results_json, response_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    query_text,
                    kst_now.isoformat(),
                    kst_now.isoformat(),
                    len(product_results),
                    len(bugs_results),
                    len(product_results) + len(bugs_results),
                    product_json,
                    bugs_json,
                    response_time_ms
                ))
                
                log_id = cursor.lastrowid
                conn.commit()
                
                self.logger.info(f"질의 로그 저장 완료 (ID: {log_id}): {query_text[:50]}...")
                return log_id
                
        except Exception as e:
            self.logger.error(f"질의 로그 저장 실패: {e}")
            return -1
    
    def get_recent_queries(self, limit: int = 50) -> List[Dict]:
        """최근 질의 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, user_id, query_text, timestamp, 
                           product_results_count, bugs_results_count, total_results_count,
                           response_time_ms
                    FROM query_logs 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"최근 질의 조회 실패: {e}")
            return []
    
    def get_query_statistics(self, days: int = 7) -> Dict:
        """질의 통계 조회"""
        try:
            # 한국 시간 기준으로 N일 전 계산
            kst_now = datetime.now(KST)
            cutoff_date = (kst_now - timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 기간별 통계
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_queries,
                        COUNT(DISTINCT user_id) as unique_users,
                        AVG(total_results_count) as avg_results,
                        AVG(response_time_ms) as avg_response_time
                    FROM query_logs 
                    WHERE timestamp >= ?
                ''', (cutoff_date,))
                
                result = cursor.fetchone()
                
                # 인기 키워드 (간단한 방식)
                cursor.execute('''
                    SELECT query_text, COUNT(*) as count
                    FROM query_logs 
                    WHERE timestamp >= ?
                    GROUP BY query_text
                    ORDER BY count DESC
                    LIMIT 10
                ''', (cutoff_date,))
                
                popular_queries = cursor.fetchall()
                
                return {
                    "period_days": days,
                    "total_queries": result[0] or 0,
                    "unique_users": result[1] or 0,
                    "avg_results_per_query": round(result[2] or 0, 2),
                    "avg_response_time_ms": round(result[3] or 0, 2),
                    "popular_queries": [{"query": q[0], "count": q[1]} for q in popular_queries]
                }
                
        except Exception as e:
            self.logger.error(f"질의 통계 조회 실패: {e}")
            return {}
    
    def search_queries(self, keyword: str, limit: int = 20) -> List[Dict]:
        """키워드로 질의 검색"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, user_id, query_text, timestamp, 
                           product_results_count, bugs_results_count, total_results_count
                    FROM query_logs 
                    WHERE query_text LIKE ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (f'%{keyword}%', limit))
                
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"질의 검색 실패: {e}")
            return []
    
    def get_query_detail(self, query_id: int) -> Optional[Dict]:
        """특정 질의의 상세 정보 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM query_logs WHERE id = ?
                ''', (query_id,))
                
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    result = dict(zip(columns, row))
                    
                    # JSON 결과 파싱
                    if result['product_results_json']:
                        result['product_results'] = json.loads(result['product_results_json'])
                    if result['bugs_results_json']:
                        result['bugs_results'] = json.loads(result['bugs_results_json'])
                    
                    return result
                return None
                
        except Exception as e:
            self.logger.error(f"질의 상세 조회 실패: {e}")
            return None
    
    def export_to_csv(self, output_file: str, days: int = 30) -> bool:
        """CSV로 내보내기"""
        try:
            import pandas as pd
            
            with sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT user_id, query_text, timestamp, 
                           product_results_count, bugs_results_count, total_results_count,
                           response_time_ms
                    FROM query_logs 
                    WHERE timestamp >= datetime('now', '-' || ? || ' days')
                    ORDER BY timestamp DESC
                '''
                
                df = pd.read_sql_query(query, conn, params=(days,))
                df.to_csv(output_file, index=False, encoding='utf-8-sig')
                
                self.logger.info(f"CSV 내보내기 완료: {output_file}")
                return True
                
        except Exception as e:
            self.logger.error(f"CSV 내보내기 실패: {e}")
            return False

if __name__ == "__main__":
    # 테스트 코드
    logger = QueryLogger()
    
    # 테스트 데이터 삽입
    test_results = {
        "product_qna": [
            {"title": "테스트 Product QnA", "url": "https://cafe.naver.com/test", "category": "Manager", "combined_score": 0.8}
        ],
        "bugs_qna": [
            {"title": "테스트 Bugs QnA", "url": "https://bugs.pnpsecure.com/view.php?id=123", "category": "Bugs", "combined_score": 0.9}
        ]
    }
    
    log_id = logger.log_query("test_user", "테스트 질의", test_results, 150.5)
    print(f"로그 ID: {log_id}")
    
    # 통계 조회
    stats = logger.get_query_statistics(7)
    print(f"통계: {stats}")
    
    # 최근 질의 조회
    recent = logger.get_recent_queries(5)
    print(f"최근 질의: {len(recent)}개") 