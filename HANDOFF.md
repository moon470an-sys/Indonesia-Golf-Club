# 작업 핸드오프 (2026-05-06, 2nd session)

다음 세션에서 그대로 이어서 작업할 수 있도록 정리.

## 라이브 사이트
**https://moon470an-sys.github.io/Indonesia-Golf-Club/?v=20260506h**

## 마지막 commit
`8d88d18` — Collect fees for 10 missing courses (4 parallel agents) — 137→148/149 priced

## 현재 상태 요약

### 데이터
- `data/golf_courses.json`: **149 코스** (운영중 137 · 휴장 9 · 불확실 3)
- **fees_2026_05 보유: 148/149** (1개 휴장 코스만 미보유)
- 직전 백업: `data/golf_courses.backup.20260506_162756.json` (10개 가격 머지 직전)
- 그 이전: `golf_courses.backup.20260506_080716.json` (12 신규 코스 추가 직전)
- 그 이전: `golf_courses.backup.20260506_070805.json` (68 finance corrections 직전)

### 사이트 탭 4개
1. **지도**: 마커 색·크기 인코딩, 줌 프리셋 5개, 범례
2. **가격 데이터**: 6 시간대 컬럼, 셀 클릭 → 출처 비교 모달
3. **재무 분석**: **50 코스** (실제 숫자 또는 티커 보유만 — 가드 강화 후)
4. **분석**: 7 차트 (KPI + 가격 분포 / 지역 / 상태 / 모회사 매출 / 설계자 / 개장년도 / 산점도)

### 사이드바
- 활성 필터 뱃지, 검색, 멀티셀렉트 지역, 가격 슬라이더, 컴팩트 chip

### 디테일 패널
- 운영상태 뱃지, 가격 매트릭스(요일×시간대), 출처별 가격 이력, 좌표 신뢰도 메모, 운영 근거 evidence

### 헤더
- KO/EN 토글, 다크모드 토글, 동적 카운트 ("총 149 · ●운영중 137 · ●휴장 9 · ●불확실 3")

## 미완료/다음 작업 후보

### 우선순위 높음
1. **재무 numbers 보강**: 50개 외에 데이터에 ticker도 없는 99개 중 가치 있는 케이스에 대해 재무 정보 수집
   - 예: matoa-nasional, royale-jakarta 같은 메이저 private 코스는 별도 수집 가치
2. **jaya-ancol-golf 가격 보완**: 이번 세션에서 모든 출처에서 published rate 미발견 (전화 +62 21 682122 only). Pinnacle Travel/Asia Medan 같은 Jakarta golf packager 추가 조사 시도 가치 있음.

### 우선순위 중간
3. **2차 verification queue**: v4 머지 후에도 12 코스가 cross-source disagreement (verification_needed=true). 추가 수동 출처 큐레이션
4. **PDF 추출 활용**: pdfplumber 경로는 있으나 현재 yield 0. 알려진 PDF 게시 사이트(Royale Jakarta, Damai Indah 등)를 fees_2026_05.sources에 직접 등록
5. **takara-golf-tigaraksa 출처 disagreement 해소**: gogolf course review (IDR 100-150k) vs gogolf summary (IDR 450-650k) vs playgolf.id (USD 23/60). 직접 확인 필요.
6. **arcamanik-raya-bandung 현행 가격**: jomkebandung 블로그(historical) 외 미발견. 전화 +62 22 7272891 확인 또는 Bandung 현지 출처 추가.

### 우선순위 낮음
7. **i18n 확장**: 현재 50+ key. 디테일 패널, 상세 데이터 헤더, 빈 상태 등이 아직 KR-only
8. **모바일 폴리쉬**: ≤480px 같은 매우 작은 화면 추가 점검

## 자동화 인프라 (재실행 가능)

### 가격 크롤 (자동 크롤러 - 광범위 패스)
```powershell
cd "C:\Users\yoonseok.moon\OneDrive - (주) ST International\Projects\Matoa 골프장\site"
python -X utf8 crawl_plan.py                    # P0/P1/P2 큐 생성
python -X utf8 crawl_runner.py --budget 3600    # 1시간 크롤
python -X utf8 merge_crawled.py --dry-run       # 미리보기
python -X utf8 merge_crawled.py                 # 백업 후 적용
```

### 가격 수집 (병렬 에이전트 - 정밀 패스, 이번 세션에 사용)
```powershell
# 1. data/agent_input/fees_chunk_*.json 작성 (코스 ID + known_evidence URLs)
# 2. Agent(general-purpose) × N 발주 — 결과는 fees_chunk_*_result.json
# 3. 머지:
python -X utf8 apply_fees_merge.py --dry-run
python -X utf8 apply_fees_merge.py
```

### 재무 검증 (4 chunk 병렬 에이전트)
```powershell
# Chunk 만들기 (필요 시 sed/python으로 chunk 다시 분할)
# Agent 발주는 Claude Code 안에서:
#   Agent(general-purpose) × 4 with discover_*.json 또는 chunk_*.json
python -X utf8 apply_finance_patches.py --dry-run
python -X utf8 apply_finance_patches.py
```

### 누락 코스 발견
```powershell
# data/agent_input/discover_*.json 생성
# Agent(general-purpose) × 4 launch
python -X utf8 apply_discovery_merge.py --dry-run
python -X utf8 apply_discovery_merge.py
```

## 주요 파일

| 파일 | 역할 |
|---|---|
| `index.html` | UI 구조 (cache-bust v=20260506g) |
| `app.js` | 모든 클라이언트 로직 (탭, 필터, 차트, i18n, 모달) |
| `style.css` | 디자인 시스템 + 반응형 |
| `data/golf_courses.json` | 메인 데이터 (149 코스) |
| `crawl_plan.py` / `crawl_runner.py` / `merge_crawled.py` | 가격 크롤 파이프라인 (v3+v4) |
| `apply_finance_patches.py` | 재무 검증 결과 머지 |
| `apply_discovery_merge.py` | 누락 코스 발견 결과 머지 |
| `data/agent_input/` | 에이전트 입력/결과 JSON 보관 |
| `VALIDATION_REPORT.md` | UI/데이터 변경 로그 |
| `README.md` | 사이트 설명 + 워크플로우 |

## 활성 background 작업
없음 — 모든 4 검증 에이전트 + 4 발견 에이전트 + 모든 monitor 종료 완료.

## 알려진 한계 (다음 세션에서 검토 가치)
- 1개 코스(jaya-ancol-golf)는 가격 데이터 부재 — 모든 published 출처가 "guide prices, confirm with course" 처리 (전화 only)
- 12개 verification 플래그 코스는 진짜 cross-source disagreement — 수동 검증 필요
- analytics 탭의 산점도가 데이터 적은 권역에서는 sparse하게 보일 수 있음
- 일부 코스는 official 사이트가 image flyer로만 rate 게시 (suvarna-jakarta 등) — `rates_visible_on_official: false` 표시
