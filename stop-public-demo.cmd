@echo off
cd /d "%~dp0"
docker compose -p family-counseling-public-demo -f docker-compose.public-demo.yml down
pause

