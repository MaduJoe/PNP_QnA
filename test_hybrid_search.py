#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from hybrid_search import HybridSearchEngine

def test_hybrid_search():
    """하이브리드 검색 시스템 테스트"""
    
    print("🚀 PNP QnA Bot 하이브리드 검색 시스템 테스트 시작\n")
    
    try:
        # 검색 엔진 초기화
        print("📊 하이브리드 검색 엔진 초기화 중...")
        search_engine = HybridSearchEngine()
        search_engine.initialize()
        print("✅ 하이브리드 검색 엔진 초기화 완료!\n")
        
        # 테스트 쿼리들
        test_queries = [
            "매니저 로그인 오류",
            "DBSAFER 설치 문제", 
            "패스워드 암호화",
            "서비스 시작 실패",
            "권한 설정 방법"
        ]
        
        print("🔍 하이브리드 검색 테스트 시작:\n")
        print("=" * 60)
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📝 테스트 {i}: '{query}'")
            print("-" * 40)
            
            # 하이브리드 검색 수행
            results = search_engine.hybrid_search(query, top_k=3)
            
            if results:
                for j, result in enumerate(results, 1):
                    print(f"   {j}. 제목: {result['title']}")
                    print(f"      카테고리: {result['category']}")
                    print(f"      종합점수: {result['combined_score']:.3f}")
                    print(f"      키워드점수: {result['keyword_score']:.3f}")
                    print(f"      임베딩점수: {result['embedding_score']:.3f}")
                    
                    # 키워드 매칭 여부 표시
                    if result['keyword_score'] > 0:
                        print(f"      ✅ 키워드 매칭됨")
                    else:
                        print(f"      🧠 의미적 유사성만")
                    
                    print(f"      URL: {result['url']}")
                    print()
            else:
                print("   검색 결과 없음")
        
        print("=" * 60)
        print("✅ 모든 테스트 완료!")
        
        # 대화형 테스트
        print("\n🎯 대화형 하이브리드 검색 테스트 (종료하려면 'quit' 입력)")
        print("-" * 40)
        
        while True:
            try:
                user_query = input("\n검색어를 입력하세요: ").strip()
                
                if user_query.lower() in ['quit', 'exit', '종료']:
                    break
                
                if not user_query:
                    continue
                
                results = search_engine.hybrid_search(user_query)
                formatted_results = search_engine.format_search_results(results, user_query)
                print(f"\n{formatted_results}")
                
                # 상세 정보 표시
                print("\n📊 상세 분석:")
                for i, result in enumerate(results, 1):
                    print(f"{i}. 키워드:{result['keyword_score']:.3f} + 임베딩:{result['embedding_score']:.3f} = 종합:{result['combined_score']:.3f}")
                
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
    success = test_hybrid_search()
    sys.exit(0 if success else 1) 