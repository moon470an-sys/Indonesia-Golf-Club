# Indonesia Golf Club Map

인도네시아 전역 **149개 골프장**(운영중 137 · 휴장 9 · 불확실 3)의 위치·요금·운영상태·출처별 가격 정보를 인터랙티브 지도로 보여주는 GitHub Pages 사이트입니다.

🔗 **Live**: https://moon470an-sys.github.io/Indonesia-Golf-Club/

## 특징

- 📍 **149개 골프장** 마커 (운영중 137 · 휴장 9 · 불확실 3) — 운영상태별 색상 + 홀 수별 크기, 우상단 줌 프리셋, 우하단 범례
- 🔍 골프장 이름·지역·설계자 검색 + 검색 가능한 지역 멀티셀렉트 + 가격 슬라이더
- 🎯 가격 데이터 탭 — 출처 점·범위·30%+ 차이 ⚠ 표시, 셀 클릭 시 출처별 가격 비교 모달 (신뢰도 정렬)
- 💼 재무 분석 탭 — 85개 골프장의 모회사·티커·매출·순이익·총자산·골프 세그먼트
- 📊 분석 탭 — 가격 분포 / 지역별 평균 / 운영 상태 / 모회사 매출 Top 10 / 설계자 / 개장년도 / 홀×가격 산점도 (Chart.js)
- 📋 디테일 패널 — 운영상태 뱃지 · 가격 매트릭스(요일×시간대) · 출처별 가격 이력 카드 · 좌표 신뢰도 메모 · 운영 근거 evidence
- 🌐 KO/EN 언어 토글, 다크모드, 키보드 a11y, prefers-reduced-motion 지원
- 📱 모바일 반응형 (≤640px 전용 폰 레이아웃 포함)
- 🆓 100% 무료 스택 (Leaflet + Chart.js + OpenStreetMap + Nominatim, 프레임워크 없음)

## 데이터

- 149개 골프장 정보를 `data/golf_courses.json`에 저장 (2026-05-01 기준; 운영중 126 · 휴장 8 · 불확실 3)
- **이용금액 (그린피·캐디·카트)**: 137개 중 106곳에 2026년 5월 기준 fees 정보 (평일/토/일 × AM/PM 6단 가격 + 출처별 다중 가격)
- **회원권 (멤버십)**: 가입비·연회비·등급별 정보 (검증된 곳에 한해)
- **🆕 기업·재무 정보 (85개 골프장)**:
  - 운영법인(PT명) · 모회사·기업집단 · IDX 상장 티커
  - 모회사 FY2024 매출/순이익/총자산 (BSDE/KPIG/BKSL/ELTY/MDLN/KIJA/MTLA/SMRA/LPKR/MKPI/PTBA/AKRA/INCO 등)
  - 골프장 단위 세그먼트 매출 (별도공시된 경우만 — 예: MDLN 골프장+클럽하우스 Rp 74.3B/2024, Palm Springs Batam Rp 42B/2024)
  - 회원권 가격 (Tier-1 공식 출처 우선: Cengkareng Rp 39.8M, Gading Raya Rp 25-65M, Emeralda Rp 55M/Rp 230M, Trump Lido USD 70K 등)
  - 모든 수치에 출처 URL + 게시일 + 출판사 명기
- 좌표는 Nominatim (OpenStreetMap 무료 지오코딩)으로 확보
- 출처: APLGI · GolfPass · GolfAsian · GolfLux · IDX · OJK · 공식 골프장 사이트 · Q-Access · 공식 SNS · 지역 뉴스

## 기술 스택

- HTML/CSS/JS (프레임워크 없음)
- [Leaflet.js](https://leafletjs.com/) — 지도 라이브러리
- [Leaflet.markercluster](https://github.com/Leaflet/Leaflet.markercluster) — 마커 클러스터링
- [CARTO Light](https://carto.com/) — 모던 베이스맵 타일

## 로컬 실행

```bash
cd site
python -m http.server 8000
# 브라우저에서 http://localhost:8000 접속
```

## 데이터 갱신 워크플로우

### 수동 큐레이션 (기존)
```bash
# 1. golf_data/golf_courses.json 수정
# 2. 누락 좌표 채우기
cd site
python geocode.py        # Nominatim으로 정확 좌표 시도 (~1초/요청)
python fallback_coords.py # 남은 좌표는 도시 중심으로 fallback

# 3. fees / financials 병합
python merge_fees.py        # 4개 fees_*.json → data/golf_courses.json
python merge_financials.py  # 4개 financials_*.json → data/golf_courses.json
```

### 자동 가격 크롤 파이프라인 (신규)
가격 데이터의 커버리지·신뢰도를 1시간 안에 자동으로 향상시키는 3-Phase 파이프라인.
**LLM 미사용** — 정규식 + BeautifulSoup + pdfplumber만 사용.

```bash
cd site

# Phase 0: 우선순위 큐 생성 (네트워크 미접근, 5초)
python -X utf8 crawl_plan.py
# → P0 (가격 0) / P1 (출처 1개 또는 슬롯 부족) / P2 (180일 stale 또는 30%+ 편차) 분류
# → data/crawl_queue.json 생성, 각 코스에 seed URL 4종 부여

# Phase 1: 1시간 hard-cap 크롤 (asyncio + httpx)
python -X utf8 crawl_runner.py --budget 3600
# → robots.txt 준수, 호스트별 1초 polite delay, 5병렬, 3회 재시도
# → 안전 출처만 (공식 사이트 link discovery / Q-Access detail follow / Wayback CDX / PDF)
# → 30초마다 data/crawl_state.json에 체크포인트 (재개 가능)
# → data/crawl_log_<ts>.json 생성

# Phase 2: 신뢰도 가중 + 호환 머지
python -X utf8 merge_crawled.py --dry-run    # 변경 미리보기
python -X utf8 merge_crawled.py              # 백업 후 적용
# → fees_2026_05.sources (string URL) 보존 + 신규 source_details (객체) + crawled_summary 추가
# → 같은 URL 내 candidates는 median으로 collapse, host간 30%+ 차이만 verification 플래그
# → data/golf_courses.backup.<ts>.json 자동 생성
```

크롤러 v3 1시간 풀 실행 결과 (2026-05-05):
- 73 코스 큐 / 38 yield / 402 candidates
- v4 머지: 168 slot summary, 12 코스에서만 진짜 cross-source disagreement
- Tier-1 (공식·정부) 67개, Tier-3 (Q-Access·GoGolf 등) 283개 신규 출처 추가

## License

데이터는 공개 출처 기반 정보의 큐레이션이며, 코드는 MIT 라이선스입니다.
