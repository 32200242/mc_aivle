# 무료 공개 시연

Docker Desktop을 실행한 뒤 저장소 루트의 `start-public-demo.cmd`를 더블클릭한다.

첫 실행에서는 Docker 이미지와 Cloudflare Tunnel 이미지를 준비하므로 몇 분 걸릴 수 있다. 준비가 끝나면 브라우저가 자동으로 열리고 PowerShell 창에 다음 형식의 주소가 표시된다.

```text
https://random-words.trycloudflare.com
```

이 주소는 계정, 카드, 도메인 없이 다른 사람에게 공유할 수 있다. PowerShell 창에서 Enter를 누르면 시연이 종료되며, 다음 실행에서는 주소가 바뀐다. 창을 강제로 닫아 서비스가 남아 있으면 `stop-public-demo.cmd`를 실행한다.

시연 로그인 계정은 다음과 같다.

- 상담사: `counselor` / `demo`
- 중앙 관리자: `admin` / `demo`

## 시연 범위와 제한

- 합성 데이터와 mock AI만 사용하며 `.env`의 실제 비밀값을 컨테이너에 전달하지 않는다.
- 공개 컨테이너 안에서 별도의 합성 DB를 생성하고 `client-00013`을 황재훈 준비 사례로 지정한다. 로컬 DB 파일은 읽거나 컨테이너에 연결하거나 Git에 업로드하지 않는다.
- 로컬 PC와 Docker Desktop이 켜져 있는 동안에만 접속할 수 있다.
- Cloudflare Quick Tunnel은 테스트·시연용이며 고정 주소와 가동 시간 보장이 없다.
- Quick Tunnel은 SSE를 공식 지원하지 않으므로 실시간 AI 응답 스트리밍은 지연되거나 동작하지 않을 수 있다. 로그인, 대시보드, 내담자 조회 등 일반 화면 시연을 권장한다.
- 최초 Docker 빌드에는 Git에서 제외된 합성 SQLite 데이터 생성 시간이 포함된다.
