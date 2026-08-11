# Render 무료 화면 시연 배포

이 구성은 `v0_5` 브랜치 전용이며 `main`의 v0.4 코드를 변경하지 않는다.

## 생성되는 공개 서비스

- 화면: `https://family-counseling-5zo.onrender.com`
- API: `https://family-counseling-5zo-api.onrender.com`
- 모드: `AI_PROVIDER=mock`, `AVATAR_PROVIDER=static_2d`
- 상담 DB: 이미지 빌드 중 결정론적으로 생성되는 합성 SQLite

서비스 이름이 Render 전체에서 이미 사용 중이면 Blueprint 생성 화면에서 두 서비스 이름을 함께 변경한다. 이 경우 프런트의 `NEXT_PUBLIC_API_BASE_URL`과 백엔드의 `CORS_ORIGINS`도 변경한 이름에 맞춘다.

## 최초 배포

1. Render에서 GitHub 계정을 연결한다.
2. **New > Blueprint**를 선택한다.
3. `32200242/mc_aivle` 저장소와 `v0_5` 브랜치를 선택한다.
4. 루트의 `render.yaml`을 확인하고 무료 서비스 2개 생성을 승인한다.
5. API 배포가 끝난 뒤 화면 배포가 완료될 때까지 기다린다.
6. 화면 URL에서 `admin / demo` 또는 `counselor / demo`로 로그인한다.

무료 서비스는 유휴 상태에서 잠들 수 있으며 첫 접속이 느릴 수 있다. 로컬 파일시스템은 재시작 시 초기화되지만, 상담 SQLite는 이미지에 들어 있으므로 다시 제공된다. 교육 진행 상태는 재시작 시 초기화되는 화면 시연용 상태다.

실제 API 키나 `.env`는 저장소에 추가하지 않는다. `AUTH_SECRET`은 Blueprint가 배포 시 자동 생성한다.
