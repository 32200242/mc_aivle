# Render Blueprint 배포

루트의 `render.yaml`은 웹 애플리케이션과 API를 두 개의 독립 서비스로 배포한다. 기본 구성은
합성 데이터와 정적 아바타를 사용하는 검증 환경이며, 운영 데이터나 외부 AI 키를 포함하지 않는다.

## 생성되는 공개 서비스

- 화면: `maum-family-center`
- API: `maum-family-center-api`
- 모드: `AI_PROVIDER=mock`, `AVATAR_PROVIDER=static_2d`
- 상담 DB: 이미지 빌드 중 고정 시드로 생성되는 합성 SQLite

Render 서비스 이름은 계정과 조직의 명명 규칙에 맞게 변경할 수 있다. 이름이나 사용자 지정
도메인을 변경하면 `NEXT_PUBLIC_API_BASE_URL`과 `CORS_ORIGINS`도 같은 주소 체계로 갱신한다.

## 최초 배포

1. 소스 저장소를 조직의 Git 제공자에 등록한다.
2. Render에서 해당 저장소와 배포 브랜치를 연결한다.
3. **New > Blueprint**에서 루트의 `render.yaml`을 선택한다.
4. 서비스 이름, 리전, 플랜, 도메인, 환경변수를 조직 정책에 맞게 검토한다.
5. API 상태 확인이 통과한 뒤 웹 애플리케이션 경로를 점검한다.
6. 검증 환경에서는 `admin / demo` 또는 `counselor / demo` 계정을 사용할 수 있다.

무료 플랜은 유휴 상태에서 중지될 수 있어 첫 요청 지연이 발생한다. 로컬 파일시스템과 교육 진행
상태는 영속 저장소가 아니며 서비스 재시작 시 초기화될 수 있다.

실제 API 키와 `.env`는 저장소에 저장하지 않는다. `AUTH_SECRET`은 Blueprint에서 생성하고,
운영 환경에서는 조직의 비밀관리 서비스와 키 순환 정책을 적용한다.
