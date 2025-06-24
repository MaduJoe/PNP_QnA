import os
import pandas as pd
import numpy as np
import pickle
import logging
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import yaml

class EmbeddingSearchEngine:
    """
    로컬 GPU 기반 임베딩 유사도 검색 엔진
    """
    
    def __init__(self, config_file="config.yaml"):
        """임베딩 검색 엔진 초기화"""
        with open(config_file, "r", encoding="utf-8") as file:
            self.config = yaml.safe_load(file)
        
        # 설정 로드
        self.embedding_config = self.config["embedding"]
        self.data_config = self.config["data"]
        
        # 모델 및 데이터 초기화
        self.model = None
        self.articles_data = None
        self.embeddings = None
        
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
            
            self.logger.info(f"총 {len(self.articles_data)}개의 게시글 로딩 완료")
            
        except Exception as e:
            self.logger.error(f"게시글 데이터 로딩 실패: {e}")
            raise
    
    def _combine_article_text(self, row) -> str:
        """게시글의 제목, 내용, 댓글을 결합"""
        title = str(row.get("제목", "")).strip()
        content = str(row.get("내용", "")).strip()
        comments = str(row.get("댓글", "")).strip()
        
        # 텍스트 결합 (제목에 가중치 부여)
        combined = f"제목: {title}\n\n"
        if content and content != "nan":
            combined += f"내용: {content}\n\n"
        if comments and comments != "nan" and comments != "댓글 없음":
            combined += f"댓글: {comments}"
        
        return combined.strip()
    
    def compute_embeddings(self, force_recompute=False):
        """게시글 임베딩 계산 및 캐시"""
        cache_file = os.path.join(
            self.embedding_config["cache_dir"], 
            "article_embeddings.pkl"
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
    
    def search_similar_articles(self, query: str, top_k: int = None) -> List[Dict]:
        """유사한 게시글 검색"""
        if top_k is None:
            top_k = self.embedding_config["top_k"]
        
        try:
            # 쿼리 임베딩 계산
            if self.model is None:
                self.load_model()
            
            query_embedding = self.model.encode([query], convert_to_tensor=False)
            
            # 코사인 유사도 계산
            similarities = cosine_similarity(query_embedding, self.embeddings)[0]
            
            # 상위 k개 인덱스 찾기
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            # 결과 생성
            results = []
            for idx in top_indices:
                article = self.articles_data.iloc[idx]
                result = {
                    "title": article["제목"],
                    "content": article["내용"][:200] + "..." if len(str(article["내용"])) > 200 else article["내용"],
                    "url": article["URL"],
                    "category": article["category"],
                    "similarity": float(similarities[idx]),
                    "게시글ID": article["게시글ID"]
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"유사도 검색 실패: {e}")
            raise
    
    def initialize(self):
        """검색 엔진 초기화"""
        self.logger.info("임베딩 검색 엔진 초기화 시작...")
        
        # 모델 로드
        self.load_model()
        
        # 데이터 로드
        self.load_articles_data()
        
        # 임베딩 계산
        self.compute_embeddings()
        
        self.logger.info("임베딩 검색 엔진 초기화 완료!")
    
    def format_search_results(self, results: List[Dict], query: str) -> str:
        """검색 결과를 사용자에게 표시할 형식으로 변환"""
        if not results:
            return "죄송합니다. 관련된 게시글을 찾을 수 없습니다."
        
        response = f"'{query}'에 대한 검색 결과입니다.\n\n"
        
        for i, result in enumerate(results, 1):
            response += f"📌 {i}. {result['title']}\n"
            response += f"카테고리: {result['category']}\n"
            response += f"유사도: {result['similarity']:.3f}\n"
            response += f"🔗 {result['url']}\n\n"
        
        return response

if __name__ == "__main__":
    # 테스트 코드
    search_engine = EmbeddingSearchEngine()
    search_engine.initialize()
    
    # 테스트 검색
    test_query = "매니저 로그인 오류"
    results = search_engine.search_similar_articles(test_query)
    print(search_engine.format_search_results(results, test_query)) 