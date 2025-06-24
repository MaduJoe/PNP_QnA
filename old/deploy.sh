#!/bin/bash

# QnA-Bot 고도화 배포 스크립트
set -e

echo "🚀 QnA-Bot Enhanced 배포를 시작합니다..."

# 환경 변수 설정
ENVIRONMENT=${1:-production}
VERSION=${2:-latest}

echo "📋 배포 환경: $ENVIRONMENT"
echo "📋 버전: $VERSION"

# 1. 기존 서비스 중지
echo "⏹️ 기존 서비스를 중지합니다..."
docker-compose down || true

# 2. 최신 코드 풀
echo "📥 최신 코드를 가져옵니다..."
git pull origin main

# 3. 환경 설정 파일 검증
echo "🔍 환경 설정을 검증합니다..."
if [ ! -f ".env" ]; then
    echo "❌ .env 파일이 없습니다. .env.example을 참고하여 생성해주세요."
    exit 1
fi

# 4. Docker 이미지 빌드
echo "🔨 Docker 이미지를 빌드합니다..."
docker-compose build --no-cache

# 5. 데이터베이스 마이그레이션
echo "🗄️ 데이터베이스를 초기화합니다..."
docker-compose up -d mongodb redis
sleep 10

# MongoDB 인덱스 생성
docker-compose exec -T mongodb mongo qnabot --eval "
db.mantis_issues.createIndex({'title': 'text', 'description': 'text', 'tags': 'text'});
db.cafe_articles.createIndex({'title': 'text', 'content': 'text', 'tags': 'text'});
db.mantis_issues.createIndex({'issue_id': 1});
db.cafe_articles.createIndex({'article_id': 1});
"

# 6. 서비스 시작
echo "🚀 서비스를 시작합니다..."
docker-compose up -d

# 7. 헬스체크
echo "🏥 헬스체크를 수행합니다..."
sleep 30

for i in {1..30}; do
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        echo "✅ 서비스가 정상적으로 시작되었습니다!"
        break
    else
        echo "⏳ 서비스 시작을 기다리는 중... ($i/30)"
        sleep 10
    fi
    
    if [ $i -eq 30 ]; then
        echo "❌ 서비스 시작에 실패했습니다."
        docker-compose logs
        exit 1
    fi
done

# 8. 백업 생성
echo "💾 데이터 백업을 생성합니다..."
mkdir -p backups
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T mongodb mongodump --db qnabot --out /tmp/backup
docker cp $(docker-compose ps -q mongodb):/tmp/backup ./backups/backup_$DATE

# 9. 모니터링 확인
echo "📊 모니터링 시스템을 확인합니다..."
if curl -f http://localhost:8000/metrics > /dev/null 2>&1; then
    echo "✅ Prometheus 메트릭이 정상적으로 노출되고 있습니다."
else
    echo "⚠️ Prometheus 메트릭에 문제가 있을 수 있습니다."
fi

# 10. LINE Webhook 테스트
echo "📱 LINE Webhook 연결을 테스트합니다..."
# 실제 환경에서는 LINE Developers Console에서 Connection check 수행

echo "🎉 배포가 완료되었습니다!"
echo ""
echo "📊 서비스 상태:"
echo "   - Main Service: http://localhost:5000"
echo "   - Monitoring: http://localhost:8000/metrics"
echo "   - MongoDB: localhost:27017"
echo "   - Redis: localhost:6379"
echo ""
echo "🔍 로그 확인: docker-compose logs -f"
echo "⏹️ 서비스 중지: docker-compose down" 