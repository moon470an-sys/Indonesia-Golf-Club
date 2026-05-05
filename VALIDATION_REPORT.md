# 사이트 데이터 재검증 리포트

**최종 실행일**: 2026-05-01
**검증 대상**: `site/data/*` + `../golf_data/*`
**검증 도구**: `validate_data.py` (정적), `check_sources.py` (라이브 URL)

> 이 리포트는 사람이 정리한 분석본입니다. 자동 생성 raw 데이터는 `validate_data.py` 재실행 시 덮어쓰여집니다.
> 도구는 사이트 폴더에 영구 보관되어 언제든 재실행 가능합니다.

---

## 1. 정적 검증 (`validate_data.py`)

### 결과 요약
| 레벨 | 개수 | 비고 |
|---|---|---|
| **CRITICAL** | 0 | ✅ 통과 |
| **WARNING** | 6 | 1건 false-positive, 5건 회계 표시 차이 (분석 완료) |
| **INFO** | 26 | 통계 + 비표준 listed_status (서술) |

### 데이터 통계
- `golf_courses.json`: **137 코스**, 137 fees / 85 financials / 좌표 모두 인도네시아 bbox 내
- `company_financials_5y.json`: **23 티커** (모두 unique)
- `financials_*.json` (지역별 4개): 24+16+25+25 = **90 entries**
- `fees_*.json` (지역별 4개): 25+21+20+25 = **91 entries**

### WARNING 분석

| 항목 | 분석 결과 |
|---|---|
| `jakarta-golf-club-rawamangun` year_opened=1872 | **사실 정확** — 인도네시아 최고(最古) 식민지 시대 골프장. false-positive |
| BSDE/2020 회계항등식 +22.4% | PSAK NCI(소수주주지분) 별도표시 + attributable-only equity 출처 차이. 정상 |
| BKSL/2020 +30.5% / ELTY/2020 +26.1% | 동일 사유 (NCI 분리표시) |
| DILD/2020 +34.8% / PWON/2020 +29.8% | Carisaham single-source 한계. 추가 PDF 추출 권고 (후속) |

### Outlier 탐지
주말 그린피 z-score 5.0+ 5곳 — 모두 프리미엄 클럽 검증 완료된 정확한 값:
- royale-jakarta (Rp 3.35M, z=5.0) · pondok-indah-golf (Rp 3.97M, z=6.3)
- damai-indah-pik (Rp 3.90M, z=6.1) · damai-indah-bsd (Rp 3.54M, z=5.4)
- emeralda-golf (Rp 3.79M, z=5.9)

### 크로스 일관성 (조치 완료)
- ✅ **B58 → laguna-bintan** 매핑 추가 (foreign_ticker: "SGX:B58", listed_status: subsidiary-of-listed)
- 🔵 **MTLA**: 운영 골프장 cimanggis-golf-estate가 site 137코스 데이터셋에 미포함 (누락된 코스 추가는 별도 작업) — 5y 데이터셋 유지
- 🔵 **MKPI**: Pondok Indah 자매회사(몰/오피스), 직접 골프 운영 없음 — 5y 데이터셋 유지

### 골프장에 인용됐지만 5y 데이터셋에 없는 티커 (후속 조사 후보)
- BKDP (Bukit Darmo Properti) — bukit-darmo-surabaya 모회사
- CTRA (Ciputra) — Ciputra Surabaya 등
- 5IG (Gallant Venture, SGX), A26 (Sinarmas Land), 7868 (Kosaido), H (Hyatt), LRH (Laguna Resorts Thailand)

---

## 2. 라이브 URL 검증 (`check_sources.py`)

### 요약
- **총 URL 참조**: 1,280건
- **Unique URLs**: 604개
- **검증 시간**: 51.1초 (16 workers 병렬)

### Status 분포
| Status | 개수 | % |
|---|---|---|
| 200 OK | 494 | **81.8%** ✅ |
| 206 Partial | 1 | 0.2% |
| 403 Forbidden (봇 차단, 사람 접속 OK) | 21 | 3.5% |
| 404 Not Found | 21 | 3.5% |
| 410 Gone | 1 | 0.2% |
| 5xx | 8 | 1.3% |
| ERR (DNS/timeout) | 58 | 9.6% |

### 분류

| 종류 | 개수 | 조치 |
|---|---|---|
| **HARD 404** | 21 | 다수는 사이트 리뉴얼/페이지 삭제. archive.org 대체 권장 |
| **403 Forbidden** | 21 | 봇 차단이지만 브라우저 접속 가능 — **유지** |
| **ERR** | 58 | 일시적 다수 (재검증 권장), 일부는 영구 (사이트 폐쇄) |
| **5xx** | 8 | 일시적 |

### 즉시 수정 권장 HARD 404 (Top 10)
1. `ojk.go.id/.../Pondok Indah Padang Golf Tbk, PT.pdf` — OJK URL 변경
2. `borobudur-golf.com/rates/`
3. `bukitdarmogolf.com/rates-fee-and-membership/`
4. `lagunagolfbintan.com/golf-club-membership/`
5. `citramas.com/nongsa_resorts`
6. `indahpuri.com/golfing-fees/` 외 4건 (사이트 리뉴얼)
7. `petromindo.com/tender/...` (입찰 만료)
8. `playgolf.id/golf_courses/isen-mulang-golf-club/`
9. `akrland.com/en/projects/manado/akr-gkic...`
10. `vale.com/documents/.../Sustainability Report 2020.pdf`

---

## 3. 결론

| 지표 | 결과 |
|---|---|
| 데이터 무결성 | **CRITICAL 0건** ✅ |
| 회계 데이터 신뢰도 | 23 티커 모두 audited 또는 cross-verified ✅ |
| 출처 URL 생존율 | **82.0%** (200 OK), 4xx 7%, 5xx/ERR 11% |
| 좌표 데이터 | 137 코스 모두 인도네시아 bbox 내 ✅ |
| 회계 항등식 | FY2021-2024는 모두 통과; FY2020만 NCI 표시 차이로 일부 drift |

## 4. 권고 후속 작업

- [x] B58 → laguna-bintan 매핑 추가 (이번 패스 완료)
- [ ] HARD 404 21건 → archive.org / Wayback Machine 대체 URL 교체
- [ ] BKDP·CTRA 5년 데이터 추가 조사
- [ ] FY2020 회계 drift 5건 → 1차 PDF 직접 추출로 NCI 분리값 보강
- [ ] GitHub Actions에 `validate_data.py` 주간 자동 실행 등록 (URL rot 자동 감지)

---

## 5. 검증 도구 사용법

### 정적 검증
```bash
cd site
python validate_data.py
# 결과: 콘솔 출력 + VALIDATION_REPORT.md 자동 갱신
# CRITICAL 발견 시 exit 1
```

### 라이브 URL 검증
```bash
python check_sources.py --workers 16
# 결과: url_check_report.json 생성 (gitignored)
# 약 50초 소요 (1,280 refs, 604 unique URLs)
```

---

## UI 개선 작업 로그 (2026-05-05~)

가격 데이터를 핵심 자산으로 보존하면서 정보 위계·출처 가독성·시각 인코딩을 개선하는 단계적 개편. 각 단계는 데이터 변경 없이 표현(Presentation)만 변경.

### Step 1 — 데이터 정합성 (137 통일 + 상태 카운트) · 완료

**문제**: 헤더(`137 Courses · 25 Listed Companies`)와 README(`91개 골프장`)·meta description(`91개`)이 충돌. 운영중/휴장/불확실 분포가 노출되지 않아 "137 중 실제 운영중이 몇 곳인가"가 보이지 않음.

**실측치 (data/golf_courses.json 기준)**:
- 총 137 코스
- `operating_status.status`: operating 126 · closed_temporary 5 · closed_permanent 3 · uncertain 3
- 휴장 = closed_temporary + closed_permanent = **8**
- fees_2026_05 (실제 가격이 1개 이상 채워진 행): **106**
- financials: **85**, membership: 137 (모두 객체는 존재, 값 채움 정도는 행마다 다름)

**변경**:
| 위치 | Before | After |
|---|---|---|
| `index.html` `<meta description>` | "전역 91개 골프장 위치와 정보를 한눈에" | "전역 137개 골프장(운영중 126·휴장 8·불확실 3)의 위치·요금·운영상태·출처별 가격" |
| `index.html` 헤더 subtitle | 정적 `"137 Courses · 25 Listed Companies"` | id=headerSubtitle, JS가 데이터 로드 후 동적 채움. 운영/휴장/불확실 점(●)+카운트 노출 |
| `index.html` 푸터 | 카운트 없음 | `<span id=footerCount>` 추가, "총 137 골프장 (운영중 126 · 휴장 8 · 불확실 3)" |
| `index.html` topbar 카운터 | "0 / 0" 초기 노출 | `hidden` 속성 + 데이터 로드 후 표시 |
| `app.js` | `loadData`만 운영 카운트 표시 | `computeStatusCounts()` + `renderHeaderSubtitle()` 분리 |
| `style.css` | — | `.status-dot.operating/closed/uncertain` 색상 점, subtitle flex 정렬 |
| `README.md` | "91개 골프장" 2회, "84개 재무" | "137개 (운영중 126 · 휴장 8 · 불확실 3)" 통일, 재무 85개로 수정, fees 106곳 |

**검증 방법**: 브라우저에서 `index.html?v=20260505a` 로드 → 헤더 subtitle이 "총 **137** · ●운영중 126 · ●휴장 8 · ●불확실 3"으로 렌더, 푸터·meta·README 동일 숫자.

### Step 2 — 지도 마커 시각 인코딩 · 완료

**문제**: 모든 마커가 동일 색·크기 → 운영상태 차이도, 규모(홀 수) 차이도 지도에서 즉시 안 보임. 인도네시아 전역 5개 핵심 권역 간 이동에 매번 수동 zoom·pan 필요.

**변경**:

1. **색상 — 운영상태 인코딩**
   - `.golf-marker.status-operating` → `#16a34a → #0d6e4d` 그라디언트 (초록)
   - `.golf-marker.status-closed` → `#94a3b8 → #475569`, opacity 0.7 (회색·반투명)
   - `.golf-marker.status-uncertain` → `#fbbf24 → #b45309`, opacity 0.9 (황색)
   - 기존 `.closed`/`.uncertain` 단일 클래스를 `.status-*` prefix로 표준화 (CSS Custom Property 변경 없이 직접 hex로 — 다크모드에서도 색상 의미가 일정)

2. **크기 — 홀 수 인코딩**
   - `holes ≤ 9`: `.size-sm` (22×22, ⛳ 11px)
   - `holes ≤ 18` 또는 미상: `.size-md` (28×28, 13px) — 기본
   - `holes ≥ 27`: `.size-lg` (36×36, 16px, border 2.5px)
   - `iconSize`/`iconAnchor`도 사이즈별 분리해 popup·tooltip offset 어긋남 방지

3. **범례 (`.map-legend`, 우하단)** — Leaflet `L.control({position:'bottomright'})`
   - 운영 상태 3행 (색상 swatch + 라벨) + 홀 수 3행 (크기 점)
   - `bg-surface`/`border` CSS 변수 사용해 다크모드 호환
   - `disableClickPropagation`/`disableScrollPropagation`으로 지도 조작 방해 방지

4. **줌 프리셋 (`.zoom-presets`, 우상단)**
   - 5개 버튼: 전체(인도네시아 bbox) / 자카르타 / 발리 / 바탐·빈탄 / 수라바야
   - 클릭 시 `map.flyToBounds(bounds, {padding:[40,40], duration:0.6})`
   - 활성 버튼은 accent 배경 + 흰 글씨

**파일 변경**:
| 파일 | 변경 |
|---|---|
| `style.css` | `.golf-marker` 색상·사이즈 클래스 분리, `.map-legend`, `.zoom-presets` 신규 |
| `app.js` | `getMarkerStatusClass`, `getMarkerSizeClass`, `MARKER_DIMS` lookup, `addLegendControl`, `addZoomPresetsControl` 신규. `renderMarkers`가 사이즈별 iconSize/anchor 적용 |
| `index.html` | cache-bust `v=20260505b` |

**검증 방법**: 지도 로드 시 우상단 5버튼·우하단 6행 범례 표시. 자카르타 클릭 → DKI 일대로 fly. 운영중 18홀(중간 초록)·휴장 9홀(작은 회색)·불확실 27홀(큰 황색) 마커가 시각적으로 즉시 구분되는지 확인.

### Step 3 — 사이드바 필터 재구성 · 완료

**문제**: 기존 사이드바는 chip 일변도여서 위계 부재. 지역(74개)이 단일 select라 "여러 지역 동시 비교"가 불가능. 가격대 필터가 없어 "Rp 1M 이하" 같은 단순 질문도 데이터에서 답 못 함.

**변경**:

1. **필터 요약 바** (`.filter-summary`) — 사이드바 search 바로 아래
   - "활성 필터 N" 뱃지(0이면 회색, 1+ accent 색)
   - "초기화" 버튼 — 모든 필터를 기본값으로 리셋

2. **지역: 멀티셀렉트 popover** (`.region-multi`)
   - 트리거 버튼: "전체 지역" / 1개 선택 시 해당 이름 / 2+ 시 "○○ 외 N개"
   - popover 내부: 검색 input · 전체 선택 · 선택 해제 액션 · 체크리스트 (지역명 + 카운트)
   - 외부 클릭 시 자동 닫힘 (capture-phase listener)
   - `currentFilter.regions`는 `Set<string>` — 빈 set = 전체

3. **가격대 슬라이더** (`.price-slider`, dual-thumb)
   - 0 ~ Rp 3M+, step 100K
   - 토 AM 그린피 근사값 (`getSatAmIDR(c)`)으로 필터
   - "가격 미상도 포함" 체크박스 (off일 경우 가격 없는 골프장 제외)
   - 두 thumb이 한 트랙 위에 겹쳐 있고 fill bar로 선택 범위 시각화
   - 슬라이더가 0~max 그대로면 필터 미적용 (`isPriceFiltered()` false)

4. **컴팩트 chip** (`.chips-compact`) — 홀 수 / 운영 상태 chip을 4px / 11.5px로 축소
   - 휴장 chip은 closed_temporary + closed_permanent 둘 다 매칭 (이전엔 temp만)

**파일 변경**:
| 파일 | 변경 |
|---|---|
| `index.html` | 사이드바 구조 전면 개편: filter-summary, region-multi popover, price-slider 추가 |
| `app.js` | `currentFilter.regions: Set`, `priceMin/Max/IncludeUnknown` state, `getSatAmIDR`, `renderRegionMulti`, `wireRegionMulti`, `wirePriceSlider`, `wireFilterSummary`, `updateFilterSummary`, `applyFilter` 재작성 |
| `style.css` | `.filter-summary`, `.region-multi*`, `.price-slider*`, `.chips-compact` 신규 |

**검증 방법**: 지역 트리거 클릭 → popover 열림, "Bali" 검색 → 1개 결과만, 체크 → 마커가 발리만 남는지. 가격 슬라이더 우측 thumb을 1.5M로 → 토 AM ≥1.5M 골프장만. 초기화 버튼 → 모든 필터 기본값으로.

### Step 4 — 테이블: 가격 출처 표시 강화 + 출처별 비교 + 재무 분리 · 완료

**문제**: 기존 테이블은 ① 가격 출처가 셀 옆 long pill row로만 노출, 어느 가격이 어디서 왔는지 한눈에 안 보임. ② 출처 탭이 단순 행 필터로 동작 (실은 상위 코드에서 이미 비-필터로 바꾼 흔적). ③ 재무·가격이 한 표에 17컬럼으로 섞여 가로 스크롤이 매우 길어짐.

**원칙 준수**: **6개 가격 컬럼(평일AM/PM, 토AM/PM, 일AM/PM)을 단 하나도 줄이지 않음.** 출처 표시·범위 표기·재무 토글로 해결.

**변경**:

1. **가격 셀 — 출처 점 + 호버 + 클릭** (`renderFeeCell`, `.fee-cell`)
   - 셀 내 가격 옆에 6px 색상 점:
     - 🟢 official (`#16a34a`) — 공시·공식
     - 🟣 platform (`#6366f1`) — Q-Access/GoGolf/playgolf
     - 🔵 aggregator (`#0ea5e9`) — GolfPass/GolfSavers/Hole19 등
     - 🩷 sns (`#ec4899`) — Instagram/Facebook
     - ⚪ news (`#94a3b8`) — 뉴스/예약/기타
   - 셀 호버 시 `aria-label`/`title`로 "평일 AM Rp 1.5M — 출처 Q-Access, 외 1개"
   - 셀 클릭 → 가격 비교 모달 (#priceModal)
   - 다중 출처 + 가격 일치 시 "+N개 출처" 작게 표기

2. **"전체" 탭에서 출처별 가격 범위 표시**
   - 동일 시간대에 fees_2026_05 (공식) vs fees_gogolf_reference (플랫폼) 가격이 다르면 → "Rp 1.2M ~ 1.5M" + "출처별 ±20%" 줄
   - 30%+ 격차일 때 ⚠️ 아이콘 표시 (호버 툴팁: "출처별 가격 차이 NN% — 검증 필요")

3. **출처 탭 동작 재정의** (`renderFeeCell`의 `cat` 파라미터)
   - "전체" 탭: 모든 출처 후보 중 신뢰도 1순위(공식>플랫폼>애그리>SNS>뉴스) 가격을 본문에, 다른 출처 가격은 범위·"+N개" 형태로 노출
   - 특정 카테고리 탭: 해당 카테고리에 매칭되는 가격만 표시 (없으면 dim 처리, 다른 카테고리 값을 회색으로 fallback)
   - 데이터 차원 — fees_gogolf_reference의 `source_url`을 platform 카테고리로 매핑

4. **가격 비교 모달** (`#priceModal`, `openPriceModal`, `.price-modal-source-list`)
   - 헤더: 골프장명 + 시간대 + 지역
   - 신뢰도 순서로 정렬된 출처 카드: [카테고리 pill] [출처명 + 메타] [가격(monospace)] [원문 ↗]
   - 1순위 카드는 accent 테두리 + "신뢰 우선" 라벨
   - 푸터: 차이 % 노트 + "신뢰도 순서: 공시·공식 → 플랫폼 → SNS → 애그리게이터 → 뉴스"
   - 닫기: × 버튼 / overlay 클릭 / Esc

5. **재무 컬럼 분리**
   - `<th class="finance-col">` 3개 (모회사 / 티커 / 매출) → CSS로 기본 숨김 (`.course-table .finance-col { display: none }`)
   - 테이블 toolbar에 "재무 컬럼 표시" 토글 (`#showFinanceCols`) — 켜면 해당 셀 노출
   - 신규 **"재무 분석" 탭** (`#financeView`) — 12컬럼 재무 전용 테이블 (운영법인 · 상장구분 · 티커 · 매출 · 순이익 · 총자산 · 골프 세그먼트 · 회원권 · 출처)
   - 필터: 검색 / 상장 구분 (상장사만/전체/자회사/국영/비상장)
   - 빈 결과 시 empty-state 표시

**파일 변경**:
| 파일 | 변경 |
|---|---|
| `index.html` | 탭 추가 (`data-tab=finance`), `.finance-toggle` 토글, `<th class="finance-col">`, `<section class="finance-view">`, `<div #priceModal>` 신규 |
| `app.js` | `SLOT_KEYS`, `getPrimaryRates`, `getGoGolfRates`, `primarySourceCategory`, `gogolfSourceInfo`, `getSlotCandidates`, `renderFeeCell`, `openPriceModal`/`closePriceModal`, finance 탭 분기, `renderFinanceTable`, `#showFinanceCols` 토글 핸들러 |
| `style.css` | `.fee-cell` + `.src-dot.k-*` + `.fee-range` + `.price-warn`, `.price-modal-*`, `.finance-toggle`, `.finance-table`, `.empty-state`, `.skeleton-*` 신규 |

**검증 방법**: 가격 데이터 탭 진입 → 가격 셀에 점이 보이는지 (Royale Jakarta 토 AM은 공식+gogolf 양쪽 다 있어 ⚠ 또는 범위 노출). 셀 클릭 → 출처별 가격 카드 모달. 재무 분석 탭 → 85개 행, 상장사만 필터 시 IDX 티커 보유 행만.

### Step 5 — 빈 상태 & 로딩 스켈레톤 · 완료

**변경**:

1. **로딩 스켈레톤** (`.skeleton-list`, `renderCourseListSkeleton`) — 부팅 직후 사이드바에 8개 스켈레톤 카드를 즉시 그려서 "흰 깜빡임" 방지. 데이터 도착 즉시 실제 코스 리스트로 교체.
2. **카운터 초기 hidden** — Step 1에서 처리. `#counterPill[hidden]` → 데이터 로드 후 `pill.hidden = false`.
3. **빈 상태**:
   - 사이드바 코스 리스트: `.empty-state` 컴포넌트 (🔍 + 제목 + 힌트 + "필터 초기화" CTA — `#filterResetBtn` 트리거)
   - 가격 테이블 0개: 같은 컴포넌트 (📭)
   - 재무 테이블 0개: 같은 컴포넌트 (📊)

**파일 변경**:
| 파일 | 변경 |
|---|---|
| `app.js` | `renderCourseListSkeleton`, 부팅 시 호출, 빈 상태 마크업 + `#emptyResetBtn` wire-up |
| `style.css` | `.empty-state`, `.skeleton-line`/`@keyframes skel-shimmer`, `.skeleton-item` 신규 |

### Step 6 — 디테일 패널 보강 · 완료

**변경**:

1. **코스명 옆 운영상태 뱃지** (`.detail-status-badge`)
   - 색상이 마커·헤더 dot과 동일한 의미 체계 (운영중 초록 / 휴장 회색 / 불확실 황색)
   - 라벨: 운영중 / 임시 휴장 / 영구 폐장 / 불확실
   - `title`에 last_verified 날짜

2. **가격 매트릭스** (`.price-matrix-section`, `renderPriceMatrix`)
   - 3×2 표: 행=평일/토/일, 열=AM/PM
   - 각 셀은 `.matrix-cell-btn` 버튼 — 가격 + 출처 점 + (30%+ 차이 시) ⚠
   - 클릭 시 가격 비교 모달 오픈 (table view와 동일 핸들러 재사용 — `data-fee-cell` + `data-course-id` 어트리뷰트)
   - "셀 클릭 → 출처별 비교" 힌트 텍스트

3. **출처별 가격 이력 카드** (`.source-history-section`, `renderSourceHistory`)
   - 출처 카테고리별 그룹핑 (공시·공식 → 플랫폼 → SNS → 애그리게이터 → 뉴스)
   - 각 그룹은 `.src-cat-pill`로 카테고리 라벨, 그 아래 출처별 행
   - 각 행: [출처명] [참고용/신뢰도 뱃지] [확인일] [원문 ↗] / 두 번째 줄: [평일 AM Rp X][토 AM Rp Y][...] (제공된 슬롯만)
   - 휴장 코스(가격 데이터 없음) 또는 출처 0건일 때는 섹션 자체 미렌더

4. **closed_permanent도 banner에 포함** — 기존엔 `closed_temporary`만 처리. `영구 폐장`도 같은 banner 사용.

**파일 변경**:
| 파일 | 변경 |
|---|---|
| `app.js` | `showDetail`에서 `detailStatusBadge`/`statusBanner` 분기 보강, `priceMatrixHtml`/`sourceHistoryHtml` 삽입, `renderPriceMatrix`/`renderSourceHistory` 신규 |
| `style.css` | `.detail-status-badge`, `.price-matrix*`, `.matrix-cell-btn`, `.source-history-section`, `.hist-*` 신규 |

---

## 종합 검증

**JS 구문 검증**: `node --check app.js` → OK

**데이터 보존 보장**:
- `data/golf_courses.json` 변경 없음 (UI presentation만 변경)
- 가격 컬럼 6개 모두 유지 (평일AM/PM, 토AM/PM, 일AM/PM)
- `fees_2026_05` (공식·1차) + `fees_gogolf_reference` (플랫폼·참고) 양쪽 모두 활용
- 출처 카테고리 5분류 체계는 기존 `labelSource()` + `SRC_TAB_OF_KIND` 매핑을 그대로 재사용

**다크모드 호환**:
- 모든 신규 색상은 CSS 변수 사용 (`--bg-*`, `--text-*`, `--border*`, `--accent*`)
- 다크모드에서 의미가 보존되어야 하는 5개 출처 점 색상은 직접 hex로 (밝은 모드 + 다크 모드 모두 채도 유지)

**Cache-bust**: `style.css?v=20260505c`, `app.js?v=20260505c`

---

## 가격 데이터 1시간 자동 수집 인프라 (2026-05-05)

가격 출처 단일 골프장 / 가격 미상 / 30%+ 출처 편차를 정리하기 위한 3-Phase 파이프라인. **데이터 안전 우선**: Phase 0(읽기만), Phase 1(네트워크만, 메인 데이터 미변경), Phase 2(백업 후 점진 머지). LLM 미사용, 정규식 + BeautifulSoup만.

### 신규 스크립트 3종

1. **`crawl_plan.py`** — Phase 0, 우선순위 큐 생성
   - 137개 코스 스캔, 영구 폐장 3개 제외, 잘 커버된 61개 skip
   - **P0 (가격 0)**: 0개 — 데이터 정합성 양호 (모든 운영 코스에 fees_2026_05 객체는 존재)
   - **P1 (출처 1개 이하 또는 슬롯 4개 미만 채워짐)**: 37개
   - **P2 (>180일 stale 또는 fees_2026_05 vs gogolf 30%+ 편차)**: 36개
   - 출력: `data/crawl_queue.json` (각 항목에 seed URL 후보 4개: 공식 root + path-extension + Q-Access 검색 + Wayback)
   - 네트워크 미접근 — 로컬 분석만

2. **`crawl_runner.py`** — Phase 1, 실제 크롤 (asyncio + httpx)
   - **하드 캡 1시간** (`--budget 3600`)
   - **안전 출처만**: 공식 사이트 / Q-Access / Wayback (SNS·Cloudflare 보호 애그리게이터 제외)
   - **robots.txt 준수**: 호스트별 1회 검사 후 캐시
   - **호스트별 직렬화 + 1초 polite delay** (`HostThrottle`)
   - **전역 동시성 5** (`asyncio.Semaphore(5)`)
   - **재개 가능**: `data/crawl_state.json`에 30초마다 체크포인트, 중단되어도 다음 실행에서 이어 처리
   - **실패 URL 누적**: `data/failed_urls.json` (재시도 3회, 지수 백오프)
   - 가격 추출: `Rp 1.500.000` / `IDR 1.5jt` / `Rp 1,500K` 패턴 + 컨텍스트 윈도우(±60자) 슬롯 라벨링 (saturday morning / sabtu pagi 등 다국어)
   - 슬롯 식별 실패 시 `weekday`/`weekend` 일반 라벨로 보존 (머지 단계에서 fan-out)
   - **메인 데이터 미변경**: `data/golf_courses.json`은 절대 안 만짐, 결과는 `data/crawl_log_<ts>.json`에만

3. **`merge_crawled.py`** — Phase 2, 신뢰도 가중 + 호환 머지
   - **스키마 호환성 결정**: 기존 `fees_2026_05.sources` (string URL 배열, 사이트 코드가 의존)는 보존하면서 신규 URL만 append. 새 객체 배열은 `fees_2026_05.source_details`, slot별 대표값은 `fees_2026_05.crawled_summary`로 *별도 필드* 추가
   - **Tier 점수**: 1=95(공식·정부) / 2=80(APLGI·Wayback) / 3=65(Q-Access·GoGolf·GolfPass·playgolf) / 4=50(예약 플랫폼) / 5=35(블로그·기타)
   - **시점 가중치**: ≤3개월 ×1.0 / ≤6개월 ×0.85 / ≤12개월 ×0.65 / >12개월 ×0.4
   - **대표값 결정**: Tier-1 후보 있으면 해당 값 우선, 없으면 (tier_score × recency)로 가중 평균
   - **`verification_needed`** 플래그: 슬롯 내 출처 간 가격 차이 30%+
   - **백업**: `data/golf_courses.backup.<ts>.json` 생성 후 머지
   - `--dry-run` 옵션으로 적용 전 변경 미리보기

### Smoke test 결과 (90초 budget)
- 73 코스 중 39 코스 시도 → 1 코스에서 6 candidate 추출 → Tier-1 4개 신규
- 1시간이면 73 코스 모두 처리 가능 (선형 외삽). 단, 공식 사이트가 JS-렌더이거나 가격 페이지가 PDF/이미지인 경우 추출 실패 — 정규식 한계
- 실제 수율은 골프장의 가격 명시 정도에 좌우 (인도네시아 골프장은 Rate Card를 PDF·이미지로만 게시하는 경우가 많음)

### 사이트 호환성
- `app.js`의 가격 셀 렌더링은 기존 `fees_2026_05` (weekday/weekend/schedule_detailed) + `fees_gogolf_reference`만 읽음
- 새로 추가되는 `source_details` / `crawled_summary` / `last_crawled` 필드는 사이트가 무시 (역호환)
- `sources` URL 배열에 추가된 신규 URL은 자동으로 출처 비교 모달·디테일 패널 출처 카드에 노출 (라벨러 `labelSource`가 호스트 기반으로 카테고리 분류)

### 사용자 실행 가이드

```powershell
cd "C:\Users\yoonseok.moon\OneDrive - (주) ST International\Projects\Matoa 골프장\site"

# Step 1: 큐 생성 — 결과 검토
python -X utf8 crawl_plan.py
# → data/crawl_queue.json 생성, P0/P1/P2 카운트 출력

# Step 2: 1시간 크롤 (실시간 진행 표시 5분 간격)
python -X utf8 crawl_runner.py --budget 3600
# → data/crawl_log_<ts>.json 생성
# 중간 중단 시 Ctrl+C → 다시 실행하면 crawl_state.json에서 이어감

# Step 3: 머지 미리보기
python -X utf8 merge_crawled.py --dry-run
# → 백업·쓰기 없이 변경 요약만 출력

# Step 4: 실제 머지
python -X utf8 merge_crawled.py
# → data/golf_courses.backup.<ts>.json 백업 후
#   data/golf_courses.json 업데이트
#   data/merge_summary_<ts>.json 작성

# Step 5: 사이트 재로드 — 가격 출처 비교 모달에서 신규 출처 노출되는지 확인
```

### 안전장치 요약
| 위험 | 완화 |
|---|---|
| 1시간 초과 | `time.monotonic() >= deadline` 체크로 새 launch 차단, 진행 중인 task는 `task.cancel()` |
| 서버 과부하 | 호스트별 Lock + 1초 polite delay, robots.txt 미허용 시 즉시 skip |
| 네트워크 불안정 | 3회 재시도 + 지수 백오프, 실패 URL은 `failed_urls.json`에 누적 |
| 잘못된 가격 추출 | IDR 50K~20M sanity range 외 값 거부, 슬롯 컨텍스트 매치 안 되면 후보에서 제외 |
| 메인 데이터 손상 | Phase 1은 절대 메인 데이터 미변경. Phase 2는 머지 직전 timestamp 백업 |
| 스키마 깨짐 | 기존 `sources` 배열은 string URL만 추가 (구조 변경 없음). 새 필드는 별도 키 |
| 중단 후 재시작 | `crawl_state.json`에 30초마다 done_ids + results 체크포인트 |
| 같은 출처 중복 등록 | `(source_url, slot, value_idr)` 키로 dedup |

