#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PNP QnA Bot 웹 대시보드 실행 스크립트
"""

import os
import sys
import webbrowser
import time
from threading import Timer

def check_dependencies():
    """필요한 의존성 패키지 확인"""
    required_packages = ['flask', 'pandas']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 필요한 패키지가 설치되지 않았습니다:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n다음 명령어로 설치해주세요:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_config():
    """설정 파일 확인"""
    if not os.path.exists("config.yaml"):
        print("❌ config.yaml 파일이 없습니다.")
        print("QnA 봇이 실행된 디렉토리에서 대시보드를 실행해주세요.")
        return False
    
    return True

def check_query_log_files():
    """질의 로그 파일들 확인"""
    files_to_check = [
        "query_logger.py",
        "templates/base.html",
        "templates/dashboard.html",
        "templates/queries.html"
    ]
    
    missing_files = []
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ 다음 파일들이 없습니다:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print("\n웹 대시보드 파일들이 올바르게 설치되었는지 확인해주세요.")
        return False
    
    return True

def open_browser():
    """브라우저에서 대시보드 열기"""
    try:
        webbrowser.open('http://localhost:8080')
        print("🌐 브라우저에서 대시보드를 열었습니다.")
    except Exception as e:
        print(f"⚠️  브라우저 자동 열기 실패: {e}")
        print("직접 http://localhost:8080 을 열어주세요.")

def main():
    """메인 함수"""
    print("🚀 PNP QnA Bot 웹 대시보드 시작")
    print("=" * 50)
    
    # 의존성 확인
    print("1. 의존성 패키지 확인 중...")
    if not check_dependencies():
        return 1
    print("✅ 의존성 패키지 확인 완료")
    
    # 설정 파일 확인
    print("2. 설정 파일 확인 중...")
    if not check_config():
        return 1
    print("✅ 설정 파일 확인 완료")
    
    # 질의 로그 파일 확인
    print("3. 대시보드 파일 확인 중...")
    if not check_query_log_files():
        return 1
    print("✅ 대시보드 파일 확인 완료")
    
    # 데이터베이스 파일 확인
    db_path = "./query_logs.db"
    if os.path.exists(db_path):
        print(f"✅ 질의 로그 데이터베이스 발견: {db_path}")
    else:
        print(f"⚠️  질의 로그 데이터베이스가 없습니다: {db_path}")
        print("QnA 봇이 실행되면 자동으로 생성됩니다.")
    
    print("\n📊 웹 대시보드 서버 시작 중...")
    print("💡 종료하려면 Ctrl+C를 누르세요")
    print("🌐 대시보드 URL: http://localhost:8080")
    print("-" * 50)
    
    # 3초 후 브라우저 열기
    timer = Timer(3.0, open_browser)
    timer.start()
    
    try:
        # 대시보드 앱 실행
        from dashboard_app import app, load_config
        
        # 설정 로드
        load_config()
        
        # Flask 앱 실행
        app.run(host='0.0.0.0', port=8080, debug=False)
        
    except KeyboardInterrupt:
        print("\n\n👋 사용자에 의해 종료되었습니다.")
        return 0
    except ImportError:
        print("\n❌ dashboard_app.py 파일을 찾을 수 없습니다.")
        print("웹 대시보드 파일이 올바르게 설치되었는지 확인해주세요.")
        return 1
    except Exception as e:
        print(f"\n❌ 대시보드 실행 중 오류 발생: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 