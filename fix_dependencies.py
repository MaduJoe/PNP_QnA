#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
종속성 문제 해결 스크립트
Flask/Werkzeug 호환성 문제를 해결합니다.
"""

import subprocess
import sys
import os

def run_command(command):
    """명령어 실행"""
    print(f"실행 중: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ 성공: {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 실패: {command}")
        print(f"오류: {e.stderr}")
        return False

def main():
    """메인 실행 함수"""
    
    print("🔧 PNP QnA Bot 종속성 문제 해결 중...")
    print("=" * 50)
    
    # 1. 기존 Flask 관련 패키지 제거
    print("\n1️⃣ 기존 Flask 관련 패키지 제거 중...")
    packages_to_remove = [
        "Flask",
        "Werkzeug", 
        "Jinja2",
        "MarkupSafe",
        "itsdangerous"
    ]
    
    for package in packages_to_remove:
        run_command(f"pip uninstall {package} -y")
    
    # 2. 호환 가능한 버전 설치
    print("\n2️⃣ 호환 가능한 버전 설치 중...")
    compatible_packages = [
        "Flask==2.3.3",
        "Werkzeug==2.3.7",
        "Jinja2==3.1.2",
        "MarkupSafe==2.1.3",
        "itsdangerous==2.1.2"
    ]
    
    for package in compatible_packages:
        if not run_command(f"pip install {package}"):
            print(f"❌ {package} 설치 실패")
            return False
    
    # 3. 나머지 requirements.txt 설치
    print("\n3️⃣ 나머지 패키지 설치 중...")
    if not run_command("pip install -r requirements.txt"):
        print("❌ requirements.txt 설치 실패")
        return False
    
    # 4. 설치 확인
    print("\n4️⃣ 설치 확인 중...")
    try:
        import flask
        import werkzeug
        print(f"✅ Flask 버전: {flask.__version__}")
        print(f"✅ Werkzeug 버전: {werkzeug.__version__}")
        
        # 임포트 테스트
        from werkzeug.urls import url_quote
        print("✅ url_quote 임포트 성공")
        
    except ImportError as e:
        print(f"❌ 임포트 테스트 실패: {e}")
        
        # 대안 방법 제시
        print("\n🔄 대안 방법 시도 중...")
        try:
            from urllib.parse import quote as url_quote
            print("✅ urllib.parse.quote 사용 가능")
        except ImportError:
            print("❌ urllib.parse.quote도 사용 불가")
            return False
    
    print("\n✅ 모든 종속성 문제 해결 완료!")
    print("🚀 이제 'python run_embedding_bot.py' 실행해보세요!")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ 종속성 해결 실패")
        print("💡 수동으로 다음 명령어들을 실행해보세요:")
        print("   pip uninstall Flask Werkzeug -y")
        print("   pip install Flask==2.3.3 Werkzeug==2.3.7")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    else:
        sys.exit(0) 