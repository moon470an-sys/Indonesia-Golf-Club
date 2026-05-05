# Indonesia Golf Club Map

인도네시아 전역 **137개 골프장**(운영중 126 · 휴장 8 · 불확실 3)의 위치·요금·운영상태·출처별 가격 정보를 인터랙티브 지도로 보여주는 GitHub Pages 사이트입니다.

🔗 **Live**: https://moon470an-sys.github.io/Indonesia-Golf-Club/

## 특징

- 📍 **137개 골프장** 마커 표시 (운영중 126 · 휴장 8 · 불확실 3 — 자카르타·발리·반둥·수라바야·빈탄·바탐 등 인도네시아 전역)
- 🔍 골프장 이름·지역·설계자 검색
- 🎯 지역별·홀 수별 필터
- 📋 마커/리스트 클릭 시 상세 정보 표시 (주소·홀 구성·설계자·부대시설·웹사이트)
- 📱 모바일 반응형
- 🆓 100% 무료 스택 (Leaflet + OpenStreetMap + Nominatim)

## 데이터

- 137개 골프장 정보를 `data/golf_courses.json`에 저장 (2026-05-01 기준; 운영중 126 · 휴장 8 · 불확실 3)
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

```bash
# 1. golf_data/golf_courses.json 수정
# 2. 누락 좌표 채우기
cd site
python geocode.py        # Nominatim으로 정확 좌표 시도 (~1초/요청)
python fallback_coords.py # 남은 좌표는 도시 중심으로 fallback

# 3. fees / financials 병합
python merge_fees.py        # 4개 fees_*.json → data/golf_courses.json
python merge_financials.py  # 4개 financials_*.json → data/golf_courses.json (재무 정보)
```

## License

데이터는 공개 출처 기반 정보의 큐레이션이며, 코드는 MIT 라이선스입니다.
