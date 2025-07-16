#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PNP QnA Bot - 로컬 GPU 임베딩 시스템 런처
"""

import os
import sys
import logging
from pnp_qna_bot_embedding import BugSearchBot

def main():
    """메인 실행 함수"""
    
    print("🚀 PNP QnA Bot - 로컬 GPU 임베딩 시스템 시작")
    print("=" * 50)
    
    try:
        # 환경 체크
        print("📊 시스템 환경 체크...")
        
        # CUDA 사용 가능 여부 확인
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0)
                print(f"✅ GPU 사용 가능: {gpu_name} (GPU 수: {gpu_count})")
            else:
                print("⚠️  GPU 사용 불가 - CPU 모드로 실행됩니다")
        except ImportError:
            print("⚠️  PyTorch 미설치 - CPU 모드로 실행됩니다")
        
        # 데이터 파일 체크
        data_files = [
            "./scripts/cafe_articles_dbs.csv",
            "./scripts/cafe_articles_mgr.csv",
            "./scripts/cafe_articles_sa.csv",
            "./scripts/mantis_bugs_20250715_150341.csv"
        ]
        
        for file_path in data_files:
            if os.path.exists(file_path):
                print(f"✅ 데이터 파일 확인: {file_path}")
            else:
                print(f"❌ 데이터 파일 없음: {file_path}")
                return
        
        # 설정 파일 체크
        if os.path.exists("config.yaml"):
            print("✅ 설정 파일 확인: config.yaml")
        else:
            print("❌ 설정 파일 없음: config.yaml")
            return
        
        print("\n🤖 라인봇 서버 시작 중...")
        print("💡 초기화 중에는 시간이 걸릴 수 있습니다 (임베딩 모델 로딩)")
        print("🔧 GPU가 있는 경우 첫 실행 시 모델 다운로드가 진행됩니다")
        print("-" * 50)
        
        # 라인봇 실행
        bot = BugSearchBot(config_file="config.yaml")
        bot.run()
        
    except KeyboardInterrupt:
        print("\n\n👋 사용자에 의해 종료되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        logging.error("라인봇 실행 중 오류", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
