# 가족센터 데이터 카탈로그

카탈로그 기준일: 2026-08-19

## 1. 데이터 포트폴리오

이 카탈로그는 가족센터 통합 플랫폼에서 사용하는 상담 사례·운영 대시보드와 기능 점검에 사용한
OCR·KMI 외부 합성 데이터의 구조와 품질 경계를 정의합니다. 상담·운영·OCR 자산은 고정 시드로
생성한 합성 자료이며, KMI는 출처와 라이선스를 별도로 표시한 외부 합성 데이터입니다.

| 도메인 | 위치 | 형식 | 주요 소비 영역 |
|---|---|---|---|
| 상담 사례 | `counseling/` | SQLite 3 | 내담자 목록, 사례 상세, 회기 기록, 코파일럿 |
| 운영 대시보드 | `dashboard/` | CSV, GZIP CSV, JSON | 관리자 대시보드, 수요예측, 인력·대기열 지표 |
| OCR 대표 하위집합 | `확인용_데이터셋/OCR/` | JSON, JSONL, CSV, PNG | OCR 데이터 계약 확인, 입력 조건 비교, 모델 후보 평가 |
| KMI 외부 합성대화 | `확인용_데이터셋/발화평가_KMI/` | JSON, TXT | 상담사 발화 훈련용 자체 규칙의 동작 방향 점검 |

### 데이터 거버넌스 분류

| 항목 | 분류 |
|---|---|
| 데이터 성격 | 고정 시드 합성·시뮬레이션 데이터 |
| 실제 인물 정보 | 포함하지 않음 |
| 개인정보·민감정보 | 포함하지 않음 |
| 실제 기관 운영 실적 | 포함하지 않음 |
| 임상적 판단 근거 | 사용 불가 |
| 대표 활용 | 기능 확인, 집계 로직 점검, 모델 후보의 제한적 상대 비교 |

## 2. 상담 사례 데이터

### 2.1 자산 프로필

| 속성 | 값 |
|---|---|
| 자산명 | `counseling_demo_v3.sqlite3` |
| 형식 | SQLite 3 |
| 생성 시드 | `20260807` |
| 데이터 기준시각 | `2026-08-10T09:00:00` |
| 내담자 | 14,143명 |
| 상담사-내담자 배정 | 14,143건 |
| 상담 회기 | 56,572건 |
| 설문 문항 정의 | 74개 |
| 설문 응답 | 1,046,582건 |
| 계산 점수 | 113,144건 |
| 설문 점수체계 | `family-questionnaires-2013-original-v1` |

### 2.2 테이블 스키마

| 테이블 | 주요 식별자 | 내용 |
|---|---|---|
| `dataset_metadata` | `key` | 데이터 유형, 생성 시드, 기준시각, 주요 건수 |
| `clients` | `id` | 합성 사례 기본정보, 주호소, 위험단계, 상담 목표, 일정 상태 |
| `counselor_client_assignments` | `client_id` | 상담사·센터·지역 배정 관계 |
| `questionnaire_items` | `item_id` | 문항 영역, 척도 범위, 역채점 여부, 출처 |
| `questionnaire_responses` | `client_id + item_id` | 사례별 문항 원응답 |
| `assessment_scores` | `client_id + code` | 척도별 계산 점수와 합성 해석값 |
| `counseling_sessions` | `id` | 회기 목표, 내담자 보고, 관찰, 개입, 반응, 다음 계획 |

### 2.3 관계

- `clients.id = counselor_client_assignments.client_id`
- `clients.id = questionnaire_responses.client_id`
- `questionnaire_items.item_id = questionnaire_responses.item_id`
- `clients.id = assessment_scores.client_id`
- `clients.id = counseling_sessions.client_id`

이름, 사례 코드, 직업, 가족구성, 회기 서술은 제품의 조회 계약을 재현하기 위한 합성값입니다.
점수와 위험단계는 실제 개인의 위험도, 진단 또는 상담 성과로 해석할 수 없습니다.

### 2.4 계보

- 생성기: `backend/scripts/build_counseling_dataset.py`
- 설문 정의와 채점 로직: `backend/app/questionnaire.py`
- 조회 계약: `backend/app/services/client_repository.py`
- 데이터 메타데이터: SQLite `dataset_metadata` 테이블

## 3. 운영 대시보드 데이터

### 3.1 자산 프로필

| 속성 | 값 |
|---|---|
| 생성 시드 | `20260803` |
| 기준일 | `2026-08-03` |
| 이력 범위 | 760일 |
| 지역 | 17개 |
| 센터 | 244개 |
| 상담인력 | 1,724명 |
| 내담자군 | 5,781행 |
| 일별 센터 지표 | 185,440행 |
| 예측 후보 | 5개 |

### 3.2 파일 스키마

| 파일 | 형식·행 수 | 주요 내용 |
|---|---:|---|
| `regions.csv` | CSV, 17행 | 지역 식별자, 센터 수, 인구·가구 기준값, 지도 좌표 |
| `centers.csv` | CSV, 244행 | 센터 유형, 지역 관계, 수요·품질 지표, 상담인력·활성 사례 수 |
| `counselors.csv` | CSV, 1,724행 | 고용형태, 경력, 주간 수용량, 활용률, 교육 이수율, 전문영역 |
| `client_cohorts.csv` | CSV, 5,781행 | 상담사·센터·지역별 주제와 관리단계별 사례 수 |
| `daily_center_metrics.csv.gz` | GZIP CSV, 185,440행 | 일자별 상담·접수·종결·노쇼·대기·만족도·슈퍼비전 지표 |
| `model_leaderboard.csv` | CSV, 5행 | 수요예측 후보별 MAE·MAPE |
| `dashboard_snapshot.json` | JSON | 화면과 API에서 사용하는 파생 집계·예측 스냅샷 |
| `metadata.json` | JSON | 생성 조건, 관계, 모델 설정, 운영계획 가정, 품질 한계 |

### 3.3 관계

- `regions.id = centers.region_id`
- `centers.id = counselors.center_id`
- `counselors.id = client_cohorts.counselor_id`
- `centers.id = daily_center_metrics.center_id`

예측과 대기열 값은 합성 이력에서 산출한 운영계획 지표입니다. 실제 가족센터의 수요, 인력
적정성, 만족도 또는 서비스 성과를 의미하지 않습니다. Erlang-C 기반 값에는 포아송 도착,
독립 서비스, 대기 이탈 없음 등의 단순화 가정이 적용됩니다.

### 3.4 계보

- 생성기: `backend/scripts/export_dashboard_dataset.py`
- 운영 데이터 모델: `backend/app/services/operational_data.py`
- 수요예측 로직: `backend/app/services/demand_forecast.py`
- 대기열 로직: `backend/app/services/queue_planning.py`
- 데이터 메타데이터: `dashboard/metadata.json`

## 4. OCR 대표 하위집합

OCR 대표 하위집합은 현재 애플리케이션의 런타임 입력이 아니라 기능 점검에 사용한 확인용 데이터입니다.

### 4.1 포함 자산

OCR 자산은 한 개 시나리오만으로 완결되는 대표 하위집합입니다.

| 항목 | 포함 범위 |
|---|---:|
| 생성 시드 | `20260805` |
| 시나리오 | 1개: `scenario-0000` |
| 필드 manifest | 16개 |
| 필드 이미지 | 16개 |
| 빈 SOAP 양식 | 1개 |
| 변형 조건 | `clean`, `scan`, `phone`, `hard` |
| SOAP 영역 | `S`, `O`, `A`, `P` |

`scenarios.jsonl`은 `scenario-0000`의 S/O/A/P 문장과 중요 용어를 정의합니다.
`field_manifest.jsonl`의 16개 레코드는 각각 `fields/*.png` 한 개와 연결되며, 네 변형과 네
SOAP 영역의 직교 조합을 구성합니다. `soap_template.png`는 영역 배치와 crop 좌표를 해석하기
위한 빈 양식입니다.

### 4.2 원천 코퍼스 참조

`dataset_card.json`은 대표 하위집합과 원천 합성 코퍼스의 규모를 분리해 기록합니다.

| 범위 | 시나리오 | 페이지 | 필드 | 줄 |
|---|---:|---:|---:|---:|
| 포함 자산 | 1 | 해당 없음 | 16 | 해당 없음 |
| 원천 코퍼스 | 12 | 48 | 192 | 528 |

페이지·줄 단위 자산은 원천 코퍼스의 규모를 설명하는 참조값이며 현재 하위집합의 데이터 계약은
`scenarios.jsonl`과 `field_manifest.jsonl`입니다. 글꼴은 파일명만, 양식은
`soap_template.png`의 상대 식별자로 기록됩니다.

### 4.3 스키마

| 파일 | 주요 필드 | 내용 |
|---|---|---|
| `dataset_card.json` | `included_scope`, `source_corpus`, `fonts`, `template`, `limitation` | 포함 범위, 원천 규모, 생성 계보, 품질 경계 |
| `scenarios.jsonl` | `scenario_id`, `session`, `sections`, `critical_terms` | 한 개 SOAP 시나리오의 기준 문장 |
| `field_manifest.jsonl` | `sample_id`, `source_id`, `image_path`, `reference`, `variant`, `section` | 이미지-참조문-변형-영역 연결 |
| `fields/*.png` | 파일명 규칙 | `scenario-0000__{variant}__field-{section}.png` |
| `soap_template.png` | PNG | SOAP 영역 배치와 좌표의 기준 양식 |

### 4.4 계보와 품질 경계

- 이미지 생성과 평가 시드는 `20260805`입니다.
- 이미지는 한글 글꼴 렌더링과 알고리즘 변형으로 생성했습니다.
- 실제 상담사 필체나 실제 상담 문서를 포함하지 않습니다.
- 16개 이미지는 입력 형식과 왜곡 조건을 확인하는 대표 하위집합이며 모집단 표본이 아닙니다.
- 이 자산만으로 OCR의 실환경 CER, WER 또는 중요정보 정확도를 추정할 수 없습니다.
- 모델 간 결과는 같은 참조문과 같은 전처리 조건을 적용했을 때에만 상대 비교가 가능합니다.

## 5. 공통 거버넌스

### 적합한 활용

- API·화면의 데이터 계약 확인
- 관계형 조회와 집계 로직 점검
- 합성 이력 기반 예측·대기열 파이프라인의 동작 확인
- OCR 어댑터의 입력·출력 형식 확인
- 동일 조건에서의 모델 후보 상대 비교

### 적합하지 않은 활용

- 실제 개인의 임상 위험 또는 상담 필요도 판단
- 실제 기관의 실적·성과·인력 적정성 산출
- 모집단 통계 또는 정책 효과 추정
- 실제 필기 OCR 정확도의 일반화
- 자동 의사결정이나 외부 공표 지표의 근거

### 관리 원칙

- 생성 시드와 `dataset_metadata` 또는 `metadata.json`을 데이터 버전의 핵심 식별자로 관리합니다.
- 스키마, 행 수, 점수체계, 생성 기준일이 바뀌면 이 카탈로그와 자산 메타데이터를 함께 갱신합니다.
- 실제 운영 데이터와 혼합할 경우 합성 여부를 레코드 또는 저장영역 수준에서 명확히 구분합니다.
- 민감정보가 유입되는 운영 환경에서는 이 합성 자산과 별도의 접근통제·보존정책을 적용합니다.
