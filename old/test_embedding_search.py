#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from embedding_search import EmbeddingSearchEngine

def test_embedding_search():
    """임베딩 검색 시스템 테스트"""
    
    print("🚀 PNP QnA Bot 임베딩 검색 시스템 테스트 시작\n")
    
    try:
        # 검색 엔진 초기화
        print("📊 검색 엔진 초기화 중...")
        search_engine = EmbeddingSearchEngine()
        search_engine.initialize()
        print("✅ 검색 엔진 초기화 완료!\n")
        
        # 테스트 쿼리들
        test_queries = [
            "매니저 로그인 오류",
            "DBSAFER 설치 문제",
            "MySQL 연결 에러",
            "서비스 시작 실패",
            "권한 설정 방법"
        ]
        
        print("🔍 테스트 검색 시작:\n")
        print("=" * 60)
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📝 테스트 {i}: '{query}'")
            print("-" * 40)
            
            # 검색 수행
            results = search_engine.search_similar_articles(query, top_k=3)
            
            if results:
                for j, result in enumerate(results, 1):
                    print(f"   {j}. 제목: {result['title']}")
                    print(f"      카테고리: {result['category']}")
                    print(f"      유사도: {result['similarity']:.3f}")
                    print(f"      URL: {result['url']}")
                    print()
            else:
                print("   검색 결과 없음")
        
        print("=" * 60)
        print("✅ 모든 테스트 완료!")
        
        # 대화형 테스트
        print("\n🎯 대화형 테스트 모드 (종료하려면 'quit' 입력)")
        print("-" * 40)
        
        while True:
            try:
                user_query = input("\n검색어를 입력하세요: ").strip()
                
                if user_query.lower() in ['quit', 'exit', '종료']:
                    break
                
                if not user_query:
                    continue
                
                results = search_engine.search_similar_articles(user_query)
                formatted_results = search_engine.format_search_results(results, user_query)
                print(f"\n{formatted_results}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"오류 발생: {e}")
        
        print("\n👋 테스트 종료")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_embedding_search()
    sys.exit(0 if success else 1) 