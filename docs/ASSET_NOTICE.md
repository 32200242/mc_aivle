# 2D 가상 페르소나 자산 안내

교육 화면은 `frontend/public/personas/lee-jieun/`과 `frontend/public/personas/kim-minseok/`의 감정별 2D 사진을 각각 6장 사용합니다. 모두 특정 실존 인물을 복제하지 않고 생성한 성인 가상 인물이며, 화면에서도 가명과 가상 페르소나임을 표시합니다.

- `neutral.png`: 차분한 기본 표정
- `sad.png`, `angry.png`, `anxious.png`, `hurt.png`, `withdrawn.png`: 동일 인물의 절제된 감정 기준 사진
- 여성 폴더에는 용량 절감을 위한 WebP 사본도 있으며 현재 화면과 백엔드는 공통 PNG를 우선 사용합니다.
- 남성 표정 세트는 2026-08-05 생성·편집했으며 인물, 배경, 의상과 정면 구도를 고정하고 얼굴 표정만 변경했습니다.
- 사진은 표정 선택과 선택적 LongCat 아바타 영상 입력에만 사용하며, 얼굴 인식·신원 확인·진단 모델 학습 데이터로 사용하지 않습니다.
- 외부 공개 전에는 생성 경위, 사용 모델·일자, 내부 승인 내역을 자산대장에 보관하세요.
- 실제 사람 사진으로 교체하려면 별도의 명시적 동의, 초상 이용 범위, 보존·파기 정책과 재생성물 이용 조건이 필요합니다.

기존 `frontend/public/models/Female_Adult_01_facial_1024.glb`는 롤백 참고용으로만 남아 있으며 현재 프런트 코드에서 로드하지 않습니다. 새 배포 산출물에서는 필요하면 별도 보관 후 제외할 수 있습니다.

LongCat-Video-Avatar 1.5 코드와 모델 가중치는 MIT 라이선스입니다. 운영 배포 시점에는 사용한 커밋, 모델 가중치, 라이선스 원문을 다시 확인해 증빙으로 보관하세요.

- 모델: `meituan-longcat/LongCat-Video-Avatar-1.5`
- 모델 카드: https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5
- 코드 및 라이선스: https://github.com/meituan-longcat/LongCat-Video

## 대한민국 시·도 지도

관리자 대시보드의 대한민국 17개 시·도 행정경계는 국가데이터처 SGIS의 2025년 2분기 시도 경계 SHP를 SVG path로 변환해 프로젝트 내부에서 사용합니다.

- 출처: [국가데이터처_SGIS 행정구역 통계 및 경계_20250630](https://www.data.go.kr/data/15129688/fileData.do)
- 이용허락범위: 제한 없음
- 원본 파일: `bnd_sido_00_2025_2Q.shp` 및 부속 DBF·CPG
- 변환 스크립트: `backend/scripts/build_sgis_svg_map.py`
- 내부 결과물: `frontend/data/southKoreaSgis.ts`, `frontend/public/maps/south-korea-sgis.svg`
- 지도 데이터는 프런트엔드 번들에 포함되므로 실행 중 외부 지도 서버에 접속하지 않으며, 화면 내 출처 표시는 요구되지 않습니다.
- 시각화와 지역 선택을 위한 경계이며 법적·측량 목적의 경계 자료로 사용하지 않습니다.
