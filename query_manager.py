#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Query Manager - 질의 로그 조회 및 관리 도구
명령행 인터페이스를 통해 질의 로그를 쉽게 조회하고 관리할 수 있는 도구
"""

import argparse
import sys
from datetime import datetime
from query_logger import QueryLogger
import yaml

def print_separator():
    """구분선 출력"""
    print("=" * 80)

def print_query_list(queries, title="질의 목록"):
    """질의 목록을 테이블 형태로 출력"""
    if not queries:
        print(f"\n{title}: 데이터가 없습니다.")
        return
    
    print(f"\n{title} (총 {len(queries)}개)")
    print_separator()
    print(f"{'ID':<5} {'사용자ID':<15} {'질의내용':<30} {'시간':<20} {'P/B/T':<8} {'응답시간':<10}")
    print_separator()
    
    for query in queries:
        query_text = query['query_text'][:28] + "..." if len(query['query_text']) > 30 else query['query_text']
        timestamp = query['timestamp'][:19] if query['timestamp'] else ""
        user_id = query['user_id'][:13] + "..." if len(query['user_id']) > 15 else query['user_id']
        
        product_count = query.get('product_results_count', 0)
        bugs_count = query.get('bugs_results_count', 0)
        total_count = query.get('total_results_count', 0)
        result_counts = f"{product_count}/{bugs_count}/{total_count}"
        
        response_time = f"{query.get('response_time_ms', 0):.0f}ms" if query.get('response_time_ms') else "N/A"
        
        print(f"{query['id']:<5} {user_id:<15} {query_text:<30} {timestamp:<20} {result_counts:<8} {response_time:<10}")

def print_query_detail(query):
    """질의 상세 정보 출력"""
    if not query:
        print("질의를 찾을 수 없습니다.")
        return
    
    print(f"\n질의 상세 정보 (ID: {query['id']})")
    print_separator()
    print(f"사용자 ID: {query['user_id']}")
    print(f"질의 내용: {query['query_text']}")
    print(f"질의 시간: {query['timestamp']}")
    print(f"응답 시간: {query.get('response_time_ms', 0):.2f}ms")
    print(f"Product QnA 결과 수: {query.get('product_results_count', 0)}")
    print(f"Bugs QnA 결과 수: {query.get('bugs_results_count', 0)}")
    print(f"총 결과 수: {query.get('total_results_count', 0)}")
    
    # Product QnA 결과
    if query.get('product_results'):
        print(f"\n💻 Product QnA 결과:")
        for i, result in enumerate(query['product_results'], 1):
            print(f"  {i}. {result['title']}")
            print(f"     카테고리: {result['category']}, 점수: {result['combined_score']:.3f}")
            print(f"     URL: {result['url']}")
    
    # Bugs QnA 결과
    if query.get('bugs_results'):
        print(f"\n🐛 Bugs QnA 결과:")
        for i, result in enumerate(query['bugs_results'], 1):
            print(f"  {i}. {result['title']}")
            print(f"     카테고리: {result['category']}, 점수: {result['combined_score']:.3f}")
            print(f"     URL: {result['url']}")

def print_statistics(stats):
    """통계 정보 출력"""
    if not stats:
        print("통계 데이터가 없습니다.")
        return
    
    print(f"\n📊 질의 통계 (최근 {stats['period_days']}일)")
    print_separator()
    print(f"총 질의 수: {stats['total_queries']:,}개")
    print(f"고유 사용자 수: {stats['unique_users']:,}명")
    print(f"평균 결과 수: {stats['avg_results_per_query']:.2f}개/질의")
    print(f"평균 응답 시간: {stats['avg_response_time_ms']:.2f}ms")
    
    if stats['popular_queries']:
        print(f"\n🔥 인기 질의 (TOP 10):")
        for i, query in enumerate(stats['popular_queries'], 1):
            print(f"  {i:2d}. {query['query']} ({query['count']}회)")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="PNP QnA Bot 질의 로그 관리 도구")
    
    # 데이터베이스 경로 옵션
    parser.add_argument('--db', default="./query_logs.db", 
                       help="SQLite 데이터베이스 파일 경로 (기본값: ./query_logs.db)")
    
    # 서브 명령어 설정
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')
    
    # 최근 질의 조회
    recent_parser = subparsers.add_parser('recent', help='최근 질의 조회')
    recent_parser.add_argument('--limit', type=int, default=20, help='조회할 질의 수 (기본값: 20)')
    
    # 질의 검색
    search_parser = subparsers.add_parser('search', help='키워드로 질의 검색')
    search_parser.add_argument('keyword', help='검색할 키워드')
    search_parser.add_argument('--limit', type=int, default=20, help='조회할 질의 수 (기본값: 20)')
    
    # 질의 상세 조회
    detail_parser = subparsers.add_parser('detail', help='특정 질의 상세 조회')
    detail_parser.add_argument('id', type=int, help='질의 ID')
    
    # 통계 조회
    stats_parser = subparsers.add_parser('stats', help='질의 통계 조회')
    stats_parser.add_argument('--days', type=int, default=7, help='통계 기간 (일) (기본값: 7)')
    
    # CSV 내보내기
    export_parser = subparsers.add_parser('export', help='CSV로 내보내기')
    export_parser.add_argument('output', help='출력 파일명')
    export_parser.add_argument('--days', type=int, default=30, help='내보낼 기간 (일) (기본값: 30)')
    
    # 실시간 모니터링
    monitor_parser = subparsers.add_parser('monitor', help='실시간 질의 모니터링')
    monitor_parser.add_argument('--interval', type=int, default=5, help='새로고침 간격 (초) (기본값: 5)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # QueryLogger 초기화
        query_logger = QueryLogger(args.db)
        
        if args.command == 'recent':
            queries = query_logger.get_recent_queries(args.limit)
            print_query_list(queries, f"최근 질의 {args.limit}개")
            
        elif args.command == 'search':
            queries = query_logger.search_queries(args.keyword, args.limit)
            print_query_list(queries, f"'{args.keyword}' 검색 결과")
            
        elif args.command == 'detail':
            query = query_logger.get_query_detail(args.id)
            print_query_detail(query)
            
        elif args.command == 'stats':
            stats = query_logger.get_query_statistics(args.days)
            print_statistics(stats)
            
        elif args.command == 'export':
            success = query_logger.export_to_csv(args.output, args.days)
            if success:
                print(f"✅ CSV 내보내기 완료: {args.output}")
            else:
                print("❌ CSV 내보내기 실패")
                
        elif args.command == 'monitor':
            print("실시간 질의 모니터링을 시작합니다. (Ctrl+C로 종료)")
            print_separator()
            
            try:
                import time
                last_id = 0
                
                while True:
                    queries = query_logger.get_recent_queries(10)
                    if queries:
                        new_queries = [q for q in queries if q['id'] > last_id]
                        if new_queries:
                            for query in reversed(new_queries):  # 시간순으로 정렬
                                print(f"[{query['timestamp']}] {query['user_id']}: {query['query_text']}")
                                last_id = max(last_id, query['id'])
                    
                    time.sleep(args.interval)
                    
            except KeyboardInterrupt:
                print("\n모니터링을 종료합니다.")
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 