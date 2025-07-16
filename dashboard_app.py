#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PNP QnA Bot 질의 로깅 웹 대시보드
Flask 기반의 실시간 질의 모니터링 및 분석 대시보드
"""

from flask import Flask, render_template, jsonify, request, send_file
from query_logger import QueryLogger
import json
from datetime import datetime, timedelta, timezone
import os
import sqlite3
import yaml

# 한국 시간대 설정 (UTC+9)
KST = timezone(timedelta(hours=9))

# Flask 앱 초기화
app = Flask(__name__)
app.secret_key = 'pnp_qna_dashboard_secret_key'

# 글로벌 설정
config = {}
query_logger = None

def load_config():
    """설정 파일 로드"""
    global config, query_logger
    try:
        if os.path.exists("config.yaml"):
            with open("config.yaml", "r", encoding="utf-8") as file:
                config = yaml.safe_load(file)
        
        # QueryLogger 초기화
        db_path = config.get("query_logging", {}).get("db_path", "./query_logs.db")
        query_logger = QueryLogger(db_path)
        print(f"✅ 설정 로드 완료: {db_path}")
        
    except Exception as e:
        print(f"❌ 설정 로드 실패: {e}")
        # 기본 설정으로 초기화
        query_logger = QueryLogger()

@app.route('/')
def dashboard():
    """메인 대시보드 페이지"""
    return render_template('dashboard.html')

@app.route('/api/stats')
def api_stats():
    """통계 API"""
    try:
        days = request.args.get('days', 7, type=int)
        stats = query_logger.get_query_statistics(days)
        
        # 한국 시간 기준으로 N일 전 계산
        kst_now = datetime.now(KST)
        cutoff_date = (kst_now - timedelta(days=days)).isoformat()
        
        # 추가 통계 계산
        with sqlite3.connect(query_logger.db_path) as conn:
            cursor = conn.cursor()
            
            # 시간대별 질의 수
            cursor.execute('''
                SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                FROM query_logs 
                WHERE timestamp >= ?
                GROUP BY strftime('%H', timestamp)
                ORDER BY hour
            ''', (cutoff_date,))
            hourly_data = dict(cursor.fetchall())
            
            # 일별 질의 수
            cursor.execute('''
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM query_logs 
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date
            ''', (cutoff_date,))
            daily_data = cursor.fetchall()
            
            # 카테고리별 통계
            cursor.execute('''
                SELECT 
                    SUM(product_results_count) as total_product,
                    SUM(bugs_results_count) as total_bugs,
                    AVG(CASE WHEN product_results_count > 0 THEN response_time_ms END) as avg_product_time,
                    AVG(CASE WHEN bugs_results_count > 0 THEN response_time_ms END) as avg_bugs_time
                FROM query_logs 
                WHERE timestamp >= ?
            ''', (cutoff_date,))
            category_stats = cursor.fetchone()
        
        # 시간대별 데이터 보완 (0~23시 모든 시간 포함)
        hourly_complete = {}
        for hour in range(24):
            hourly_complete[f"{hour:02d}"] = hourly_data.get(f"{hour:02d}", 0)
        
        stats['hourly_data'] = hourly_complete
        stats['daily_data'] = daily_data
        stats['category_stats'] = {
            'total_product_results': category_stats[0] or 0,
            'total_bugs_results': category_stats[1] or 0,
            'avg_product_response_time': round(category_stats[2] or 0, 2),
            'avg_bugs_response_time': round(category_stats[3] or 0, 2)
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent_queries')
def api_recent_queries():
    """최근 질의 API"""
    try:
        limit = request.args.get('limit', 20, type=int)
        queries = query_logger.get_recent_queries(limit)
        return jsonify(queries)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search_queries')
def api_search_queries():
    """질의 검색 API"""
    try:
        keyword = request.args.get('keyword', '')
        limit = request.args.get('limit', 20, type=int)
        
        if not keyword:
            return jsonify([])
        
        queries = query_logger.search_queries(keyword, limit)
        return jsonify(queries)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/query_detail/<int:query_id>')
def api_query_detail(query_id):
    """질의 상세 API"""
    try:
        query = query_logger.get_query_detail(query_id)
        if query:
            return jsonify(query)
        else:
            return jsonify({'error': '질의를 찾을 수 없습니다.'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export_csv')
def api_export_csv():
    """CSV 내보내기 API"""
    try:
        days = request.args.get('days', 30, type=int)
        
        # 임시 파일명 생성 (한국 시간)
        timestamp = datetime.now(KST).strftime('%Y%m%d_%H%M%S')
        filename = f"query_logs_{timestamp}.csv"
        
        # CSV 생성
        success = query_logger.export_to_csv(filename, days)
        
        if success and os.path.exists(filename):
            return send_file(filename, as_attachment=True, download_name=filename)
        else:
            return jsonify({'error': 'CSV 생성 실패'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/queries')
def queries_page():
    """질의 목록 페이지"""
    return render_template('queries.html')

@app.route('/query/<int:query_id>')
def query_detail_page(query_id):
    """질의 상세 페이지"""
    return render_template('query_detail.html', query_id=query_id)

@app.route('/api/live_stats')
def api_live_stats():
    """실시간 통계 API (자동 새로고침용)"""
    try:
        # 한국 시간 기준으로 시간 계산
        kst_now = datetime.now(KST)
        cutoff_5min = (kst_now - timedelta(minutes=5)).isoformat()
        cutoff_1hour = (kst_now - timedelta(hours=1)).isoformat()
        
        with sqlite3.connect(query_logger.db_path) as conn:
            cursor = conn.cursor()
            
            # 최근 5분간 질의 수
            cursor.execute('''
                SELECT COUNT(*) FROM query_logs 
                WHERE timestamp >= ?
            ''', (cutoff_5min,))
            recent_5min = cursor.fetchone()[0]
            
            # 최근 1시간 질의 수
            cursor.execute('''
                SELECT COUNT(*) FROM query_logs 
                WHERE timestamp >= ?
            ''', (cutoff_1hour,))
            recent_1hour = cursor.fetchone()[0]
            
            # 총 질의 수
            cursor.execute('SELECT COUNT(*) FROM query_logs')
            total_queries = cursor.fetchone()[0]
            
            # 평균 응답 시간 (최근 100개)
            cursor.execute('''
                SELECT AVG(response_time_ms) FROM (
                    SELECT response_time_ms FROM query_logs 
                    WHERE response_time_ms IS NOT NULL 
                    ORDER BY timestamp DESC LIMIT 100
                )
            ''')
            avg_response_time = cursor.fetchone()[0] or 0
            
        return jsonify({
            'recent_5min': recent_5min,
            'recent_1hour': recent_1hour,
            'total_queries': total_queries,
            'avg_response_time': round(avg_response_time, 2),
            'timestamp': datetime.now(KST).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 설정 로드
    load_config()
    
    # 템플릿 및 정적 파일 디렉토리 생성
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    print("🚀 PNP QnA Bot 질의 로깅 대시보드 시작")
    print("📊 대시보드 URL: http://localhost:8080")
    print("=" * 50)
    
    # Flask 앱 실행
    app.run(host='0.0.0.0', port=8080, debug=True) 