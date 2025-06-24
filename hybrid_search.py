import os
import pandas as pd
import numpy as np
import pickle
import logging
import re
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import yaml

class HybridSearchEngine:
    """
    하이브리드 검색 엔진: 키워드 검색 + 임베딩 검색 결합
    """
    
    def __init__(self, config_file="config.yaml"):
        """하이브리드 검색 엔진 초기화"""
        with open(config_file, "r", encoding="utf-8") as file:
            self.config = yaml.safe_load(file)
        
        # 설정 로드
        self.embedding_config = self.config["embedding"]
        self.data_config = self.config["data"]
        
        # 검색 가중치 설정 (키워드에 더 높은 가중치)
        self.keyword_weight = 0.6  # 키워드 검색 가중치 증가
        self.embedding_weight = 0.4  # 임베딩 검색 가중치 감소
        
        # 모델 및 데이터 초기화
        self.model = None
        self.articles_data = None
        self.embeddings = None
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        
        # 캐시 디렉토리 생성
        os.makedirs(self.embedding_config["cache_dir"], exist_ok=True)
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def load_model(self):
        """임베딩 모델 로드"""
        try:
            self.logger.info(f"임베딩 모델 로딩 중: {self.embedding_config['model_name']}")
            self.model = SentenceTransformer(
                self.embedding_config["model_name"],
                device="cuda" if self._is_cuda_available() else "cpu"
            )
            self.logger.info("임베딩 모델 로딩 완료")
        except Exception as e:
            self.logger.error(f"모델 로딩 실패: {e}")
            raise
    
    def _is_cuda_available(self) -> bool:
        """CUDA 사용 가능 여부 확인"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def load_articles_data(self):
        """게시글 데이터 로드"""
        try:
            self.logger.info("게시글 데이터 로딩 중...")
            
            # DBS 게시글 데이터 로드
            dbs_path = os.path.join(
                self.data_config["articles_path"], 
                self.data_config["dbs_file"]
            )
            dbs_articles = pd.read_csv(dbs_path, encoding="utf-8")
            dbs_articles["category"] = "DBS"
            
            # Manager 게시글 데이터 로드
            mgr_path = os.path.join(
                self.data_config["articles_path"], 
                self.data_config["mgr_file"]
            )
            mgr_articles = pd.read_csv(mgr_path, encoding="utf-8")
            mgr_articles["category"] = "Manager"
            
            # 데이터 결합
            self.articles_data = pd.concat([dbs_articles, mgr_articles], ignore_index=True)
            
            # 텍스트 전처리
            self.articles_data["combined_text"] = self.articles_data.apply(
                self._combine_article_text, axis=1
            )
            
            # 키워드 검색용 텍스트 (제목 강조)
            self.articles_data["keyword_text"] = self.articles_data.apply(
                self._prepare_keyword_text, axis=1
            )
            
            self.logger.info(f"총 {len(self.articles_data)}개의 게시글 로딩 완료")
            
        except Exception as e:
            self.logger.error(f"게시글 데이터 로딩 실패: {e}")
            raise
    
    def _combine_article_text(self, row) -> str:
        """게시글의 제목, 내용, 댓글을 결합 (임베딩용)"""
        title = str(row.get("제목", "")).strip()
        content = str(row.get("내용", "")).strip()
        comments = str(row.get("댓글", "")).strip()
        
        # 텍스트 결합
        combined = f"{title}\n\n"
        if content and content != "nan":
            combined += f"{content}\n\n"
        if comments and comments != "nan" and comments != "댓글 없음":
            combined += f"{comments}"
        
        return combined.strip()
    
    def _prepare_keyword_text(self, row) -> str:
        """키워드 검색용 텍스트 준비 (제목에 강한 가중치 부여)"""
        title = str(row.get("제목", "")).strip()
        content = str(row.get("내용", "")).strip()
        comments = str(row.get("댓글", "")).strip()
        
        # 제목을 5번 반복하여 강한 가중치 부여
        keyword_text = f"{title} {title} {title} {title} {title}"
        
        if content and content != "nan":
            keyword_text += f" {content}"
        if comments and comments != "nan" and comments != "댓글 없음":
            keyword_text += f" {comments}"
        
        return keyword_text.strip()
    
    def setup_tfidf(self):
        """TF-IDF 벡터라이저 설정"""
        self.logger.info("TF-IDF 벡터라이저 설정 중...")
        
        # 한국어에 최적화된 TF-IDF 설정
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),  # 1-2gram 사용 (3gram은 너무 세분화)
            min_df=1,
            max_df=0.8,
            sublinear_tf=True,
            analyzer='word',  # word 단위로 변경 (한국어도 효과적)
            token_pattern=r'\b\w+\b',
        )
        
        # TF-IDF 매트릭스 생성
        texts = self.articles_data["keyword_text"].tolist()
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
        
        self.logger.info("TF-IDF 설정 완료")
    
    def compute_embeddings(self, force_recompute=False):
        """게시글 임베딩 계산 및 캐시"""
        cache_file = os.path.join(
            self.embedding_config["cache_dir"], 
            "article_embeddings_hybrid.pkl"
        )
        
        # 캐시된 임베딩이 있고 재계산이 필요없는 경우
        if os.path.exists(cache_file) and not force_recompute:
            try:
                with open(cache_file, "rb") as f:
                    self.embeddings = pickle.load(f)
                self.logger.info("캐시된 임베딩 로딩 완료")
                return
            except Exception as e:
                self.logger.warning(f"캐시된 임베딩 로딩 실패: {e}")
        
        # 임베딩 계산
        self.logger.info("게시글 임베딩 계산 중...")
        if self.model is None:
            self.load_model()
        
        texts = self.articles_data["combined_text"].tolist()
        
        # 배치 단위로 임베딩 계산
        batch_size = self.embedding_config["batch_size"]
        embeddings_list = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(
                batch_texts,
                convert_to_tensor=False,
                show_progress_bar=True,
                batch_size=min(batch_size, len(batch_texts))
            )
            embeddings_list.append(batch_embeddings)
            
            self.logger.info(f"진행률: {min(i + batch_size, len(texts))}/{len(texts)}")
        
        # 임베딩 결합
        self.embeddings = np.vstack(embeddings_list)
        
        # 캐시 저장
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(self.embeddings, f)
            self.logger.info("임베딩 캐시 저장 완료")
        except Exception as e:
            self.logger.warning(f"임베딩 캐시 저장 실패: {e}")
    
    def keyword_search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """키워드 기반 검색"""
        # 쿼리를 TF-IDF 벡터로 변환
        query_vector = self.tfidf_vectorizer.transform([query])
        
        # 코사인 유사도 계산
        similarities = cosine_similarity(query_vector, self.tfidf_matrix)[0]
        
        # 상위 k개 인덱스와 점수 반환
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = [(idx, similarities[idx]) for idx in top_indices if similarities[idx] > 0]
        
        return results
    
    def embedding_search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """임베딩 기반 검색"""
        if self.model is None:
            self.load_model()
        
        # 쿼리 임베딩 계산
        query_embedding = self.model.encode([query], convert_to_tensor=False)
        
        # 코사인 유사도 계산
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        
        # 상위 k개 인덱스와 점수 반환
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = [(idx, similarities[idx]) for idx in top_indices]
        
        return results
    
    def exact_keyword_bonus(self, query: str, article_title: str, article_text: str) -> float:
        """정확한 키워드 매칭에 대한 보너스 점수"""
        query_words = set(re.findall(r'\w+', query.lower()))
        title_words = set(re.findall(r'\w+', article_title.lower()))
        article_words = set(re.findall(r'\w+', article_text.lower()))
        
        if not query_words:
            return 0.0
        
        # 제목에서 매칭되는 경우 높은 보너스
        title_match_ratio = len(query_words.intersection(title_words)) / len(query_words)
        
        # 전체 텍스트에서 매칭되는 경우 일반 보너스
        text_match_ratio = len(query_words.intersection(article_words)) / len(query_words)
        
        # 제목 매칭에 더 높은 가중치
        total_bonus = title_match_ratio * 0.5 + text_match_ratio * 0.2
        
        return min(total_bonus, 0.7)  # 최대 0.7점 보너스
    
    def hybrid_search(self, query: str, top_k: int = None) -> List[Dict]:
        """하이브리드 검색: 키워드 + 임베딩 결합"""
        if top_k is None:
            top_k = self.embedding_config["top_k"]
        
        try:
            # 1. 키워드 검색 수행
            keyword_results = self.keyword_search(query, top_k=20)
            
            # 2. 임베딩 검색 수행
            embedding_results = self.embedding_search(query, top_k=20)
            
            # 3. 점수 정규화 및 결합
            combined_scores = {}
            
            # 키워드 검색 점수 추가
            if keyword_results:
                max_keyword_score = max([score for _, score in keyword_results])
                for idx, score in keyword_results:
                    normalized_score = score / max_keyword_score if max_keyword_score > 0 else 0
                    combined_scores[idx] = combined_scores.get(idx, 0) + normalized_score * self.keyword_weight
            
            # 임베딩 검색 점수 추가
            if embedding_results:
                max_embedding_score = max([score for _, score in embedding_results])
                for idx, score in embedding_results:
                    normalized_score = score / max_embedding_score if max_embedding_score > 0 else 0
                    combined_scores[idx] = combined_scores.get(idx, 0) + normalized_score * self.embedding_weight
            
            # 4. 정확한 키워드 매칭 보너스 추가
            for idx in combined_scores:
                article = self.articles_data.iloc[idx]
                bonus = self.exact_keyword_bonus(
                    query, 
                    article["제목"], 
                    article["combined_text"]
                )
                combined_scores[idx] += bonus
            
            # 5. 상위 k개 선택
            sorted_results = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
            
            # 6. 결과 포맷팅
            results = []
            for idx, combined_score in sorted_results:
                article = self.articles_data.iloc[idx]
                
                # 개별 점수 계산 (디버깅용)
                keyword_score = 0
                embedding_score = 0
                
                for k_idx, k_score in keyword_results:
                    if k_idx == idx:
                        keyword_score = k_score
                        break
                
                for e_idx, e_score in embedding_results:
                    if e_idx == idx:
                        embedding_score = e_score
                        break
                
                result = {
                    "title": article["제목"],
                    "content": article["내용"][:200] + "..." if len(str(article["내용"])) > 200 else article["내용"],
                    "url": article["URL"],
                    "category": article["category"],
                    "combined_score": float(combined_score),
                    "keyword_score": float(keyword_score),
                    "embedding_score": float(embedding_score),
                    "게시글ID": article["게시글ID"]
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"하이브리드 검색 실패: {e}")
            raise
    
    def initialize(self):
        """검색 엔진 초기화"""
        self.logger.info("하이브리드 검색 엔진 초기화 시작...")
        
        # 모델 로드
        self.load_model()
        
        # 데이터 로드
        self.load_articles_data()
        
        # TF-IDF 설정
        self.setup_tfidf()
        
        # 임베딩 계산
        self.compute_embeddings()
        
        self.logger.info("하이브리드 검색 엔진 초기화 완료!")
    
    def format_search_results(self, results: List[Dict], query: str) -> str:
        """검색 결과를 사용자에게 표시할 형식으로 변환"""
        if not results:
            return "죄송합니다. 관련된 게시글을 찾을 수 없습니다."
        
        response = f"🔍 '{query}' 하이브리드 검색 결과\n\n"
        
        for i, result in enumerate(results, 1):
            response += f"📌 {i}. {result['title']}\n"
            response += f"📂 카테고리: {result['category']}\n"
            response += f"🎯 종합점수: {result['combined_score']:.3f}\n"
            response += f"🔗 {result['url']}\n\n"
        
        return response

if __name__ == "__main__":
    # 테스트 코드
    search_engine = HybridSearchEngine()
    search_engine.initialize()
    
    # 테스트 검색
    test_query = "매니저 로그인 오류"
    results = search_engine.hybrid_search(test_query)
    print(search_engine.format_search_results(results, test_query)) 