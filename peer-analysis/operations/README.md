# 인도네시아 골프 운영 벤치마크 — IDX 13 peer (v2)

> **메타 문서 cross-reference**: README.md (본 문서) · [IMPROVEMENT_LOG.md](IMPROVEMENT_LOG.md) (사이클 변경) · [verification_log.md](verification_log.md) (검증) · [CORRECTIONS.md](CORRECTIONS.md) (11건 정정) · [LIMITATIONS.md](LIMITATIONS.md) (6 한계) · [INVENTORY.md](INVENTORY.md) (종합)

## 🆕 Peer Group v2 (Cycle 168, 2026-05-12)

골프 운영 정보 깊이 기준 4-tier framework로 13 peer 재구성:

| Tier | 정의 | Peer (count) |
|------|------|--------------|
| **1. Pure-play 골프** | 골프장이 100% 또는 압도적 주력 | DMIG · PIPG · GOLF (3) |
| **2. Group + Golf segment 분리 공시** | AR에서 골프 매출·비용 별도 라인 | MDLN · KIJA · SMDM (3) |
| **3. Adjacent (Hotel/Leisure 통합)** | Hotel·Resort·Leisure에 골프 포함 | KPIG · SMRA (2) |
| **4. 부동산 그룹 + 운영 골프장** | 메인은 부동산이나 1+ 운영 골프장 | BSDE · CTRA · ELTY · LPKR · PWON (5) |

**v1 → v2 변경 (4 swap)**:
- **REMOVE**: MKPI (0 골프) · BKDP (defunct, 쇼핑센터) · BKSL (관계사 운영) · DILD (Golf segment X) → `operations/data/archived/`
- **ADD**: CTRA (Ciputra 2 코스) · ELTY (Bakrieland 2 코스) · LPKR (Lippo Imperial Klub) · PWON (Pakuwon Golf)

운영 총괄 관점 + AR Note 직접 인용 기반 벤치마크 사이트.
13개 IDX 상장사 (DMIG·KPIG·MKPI·PIPG·BSDE·DILD·GOLF·MDLN·SMRA·SMDM·KIJA·BKDP·BKSL)의 FY2022-FY2024 골프 부문 운영을 비교.

---

## 빠른 시작

### 처음 방문이라면
1. **`overview.html`** TLDR — 5 핵심 발견 + 6-peer 1-card 한 화면 (Cycle 31 신규)
2. **`index.html`** — 5 카테고리 카드 + 13-peer 추출 매트릭스 + 6-peer ratio 요약

### 깊게 보고 싶다면
| 카테고리 | 페이지 | 핵심 내용 |
|---------|--------|----------|
| 단위 경제 | `unit-economics.html` | 홀당·ha당·1인당 매출. Pure-play DMIG·PIPG vs GOLF·MDLN·KIJA·SMDM. DMIG vs PIPG 인력 집약도 비교. |
| 매출 믹스 | `revenue.html` | DMIG 7 라인 + PIPG 11 라인 stacked bar. 회원권 비중 추이. 13-peer 그룹 매출 분포. |
| 비용 구조 | `cost-hr.html` | 매출원가 + OpEx 라인별 분해. 6-peer GP/OpInc 시각화. 영업이익률·매출원가율 시계열. |
| 시설 | `assets.html` | AR-cited 코스 정량 (DMIG 36 hole/156 ha · PIPG 18 hole/53 ha · GOLF 3 courses). 부속 시설 매출 기여. |
| 위험 | `risk.html` | AR 공시 위험 사례: 손실 (MDLN·BKDP) / 매출 집중 (GOLF) / 매입 집중 (MDLN) / 토지권 (PIPG) / Going Concern (BKDP). |

---

## 데이터 신뢰 등급

| 등급 | 정의 | 사이트 표시 |
|------|------|------------|
| A | AR Note 또는 income statement 직접 추출, 다중 cross-check | 녹색 ✓ + 페이지/Note 번호 인라인 |
| B | FY23/FY24 AR의 comparative column 추출 | 녹색 ✓ + "(FY23 AR comparative)" 명시 |
| C | curated CSV, AR 직접 검증 미완 | "(curated)" 표기 |
| D | curated와 AR-direct 불일치 → AR-direct로 정정 | `CORRECTIONS.md` 인용 + 정정 사유 |
| N/A | 분리 공시 없음 또는 AR 미공시 | "공시 없음" / "미공시" / "N/A" |

**Cycle 35 종료 분포:** A 등급 ~30 셀 / B ~5 셀 / C ~15 셀 / D 10 셀 / N/A ~84 셀 (총 143 셀 중).

---

## 핵심 발견 (7) — Cycle 123 갱신

### 1. 6/13 peer만 Golf segment 분리 공시
- ✓ AR 직접 추출: DMIG · PIPG · GOLF · MDLN · KIJA · SMDM
- ✗ 분리 공시 없음: KPIG (Hotel+Golf 통합) · BSDE (associate) · BKSL (관계사) · SMRA·DILD·BKDP·MKPI
- **Cycle 98·101-103 추가 검증**: BSDE·DILD·MKPI·BKSL FY25 segment Note 직접 추출 — 모두 "Golf segment 없음" 직접 확인.

### 2. Pure-play vs 그룹 segment GP 마진 격차
- Pure-play / 리조트: GOLF 65.7% · PIPG 63.4% · DMIG 58.6%
- 그룹 내 segment: MDLN 44.5% · KIJA 41.6% · SMDM 38.9%

### 3. DMIG vs PIPG 운영 모델 정반대
- DMIG (36 hole, 156 ha): 홀당 5.5명 / 1인당 매출 1,278 m Rp = 효율 중심
- PIPG (18 hole, 53 ha): 홀당 14.1명 / 1인당 매출 778 m Rp = 서비스 집약

### 4. PIPG 토지권 만료 임박
- HGB 209,533 m² 만료 2025·2055년 (FY24 AR p.131 Note 10)
- 13 peer 중 유일 AR-cited 토지권 만료년

### 5. SMDM 매출원가 급증 (단, FY25 restatement caveat)
- Golf&CC GP 마진 FY22 54.8% → FY24 38.9% (-15.9pp)
- 매출원가율 +15.9pp 악화. FY24 영업이익 -212 m (적자 전환)
- **Cycle 64·67 FY25 발견**: GP 마진 88.6% 대전환 — BSDE/Sinarmas 인수 후 회계 재분류 가능성 (Cycle 67 caveat).

### 6. FY25 follow-up era — 11/13 peer 추출 (Cycle 62-103)
- 가용: SMDM·MDLN·GOLF·KIJA·KPIG·BKDP·SMRA·BSDE·DILD·MKPI·BKSL (11 peer)
- 미가용: DMIG·PIPG (annual_reports/FY2025/ 디렉토리 부재)
- **주요 발견**: MDLN +28.2% 유기적 성장 / KPIG 회사명 변경 (MNC Tourism) / SMRA Leisure 마진 -7.2pp / BKDP 매출 +20% but Going Concern 지속 / BSDE FY25 추출로 Cycle 56 실패 해소 / KIJA FY24 cross-validation 100%.

### 7. 13/13 peer AR Note 직접 추출 완주 (Cycle 103)
- 본 사이트 사이클 1-103 동안 13 peer 모두 텍스트 기반 segment/P&L 추출 검증.
- 신규 추출 6 peer (Cycle 92-103): BKDP·SMRA·BSDE·DILD·MKPI·BKSL.
- 모두 LIMITATIONS.md A 등급 (AR-direct).

상세는 `overview.html` 또는 각 페이지 참조.

---

## 메타 문서 (5)

| 문서 | 역할 |
|------|------|
| `IMPROVEMENT_LOG.md` | 35 사이클 변경 history + 누적 작업 |
| `verification_log.md` | 페이지별 출처·수치·미공시·원칙 위반 검증 |
| `CORRECTIONS.md` | curated CSV → AR-direct 정정 11건 누적 (Cycle 86 self-correction 포함) |
| `LIMITATIONS.md` | 추출 한계 6 카테고리 + 신뢰 등급 + 극복 방안 |
| `INVENTORY.md` | 산출물 종합 인벤토리 (페이지·메타·데이터·시각화) |

---

## 데이터 JSON (13 peer 완주 + 통합 + 기존 = 15개) — **Cycle 103 13/13 완주**

원본 7 peer (Cycle 1-31):
- `data/dmig_notes.json` — DMIG Note 23/24/25 (revenue/COGS/OpEx 모든 라인 FY22-24)
- `data/pipg_notes.json` — PIPG Note 27/28/29 + p.7 Profil + p.11 Ikhtisar
- `data/golf_notes.json` — GOLF Note 29/30/31/32 + p.62 Wilayah Operasional (+FY25 Cycle 79)
- `data/mdln_notes.json` — MDLN Note 25/26/32 + segment (+FY25 Cycle 77)
- `data/kija_notes.json` — KIJA Note 34 Golf segment (+FY25 Cycle 80)
- `data/smdm_notes.json` — SMDM Note 29 5 segments FY22-24 (+FY25 caveat Cycle 78)
- `data/kpig_notes.json` — KPIG Note 31/34/35 (Hotel+Resort+Golf 통합) (+FY25 회사명 변경 Cycle 80)

Cycle 92-103 추가 추출 6 peer (FY25 AR 직접):
- `data/bkdp_notes.json` — BKDP FY25 P&L (Cycle 92) — Going Concern 후속
- `data/smra_notes.json` — SMRA FY25 Note 31/32 Leisure (Cycle 95) — GP 마진 -7.2pp
- `data/bsde_notes.json` — BSDE FY25 Informasi Segmen (Cycle 98) — Golf 없음 확인
- `data/dild_notes.json` — DILD FY25 Informasi Segmen (Cycle 101) — Golf 없음 확인
- `data/mkpi_notes.json` — MKPI FY25 Note 37 (Cycle 102) — Golf 없음 (PIPG associate)
- `data/bksl_notes.json` — BKSL FY25 Note 37 (Cycle 103) — Sentul Golf은 관계사 운영

통합:
- `data/peers_summary.json` — **13 peer 통합 (Cycle 105 79.0 KB 13/13 완주)**

---

## 추출 한계 (LIMITATIONS.md)

| 카테고리 | 영향 | 우회 방안 |
|----------|------|----------|
| 1. 이미지 PDF | DMIG·MDLN auditor's report 추출 불가 | OCR (Tesseract / Cloud Vision) — 로컬 환경 미설치 |
| 2. 회전 표 | KIJA FY23 AR Note 34 회전 표 부분 추출 | column-aware extraction (pdfplumber·camelot) |
| 3. AR 분리 미공시 | 7 peer Golf 단독 라인 없음 | 외부 source (BEI·IR·OJK) |
| 4. curated 미검증 | KIJA 47.92·SMDM 75.6·KPIG 7.36 bn 등 | AR-direct로 정정 (11건) |
| 5. FY22 시계열 부분 | GOLF FY22 (IPO 전) · KIJA FY22-23 | IPO Prospectus·회전 표 |
| 6. 정성 정보 | 회원권 단가·연회비·회원 수 0/13 | peer 홈페이지·Sustainability Report |

---

## 원칙

1. IDX 13 peer 공식 AR FY2022-FY2024에 명시 공시된 내용만 게재.
2. 추정·해석·일반론·특정 자산 비교 금지.
3. 모든 수치에 AR 페이지/Note 번호 명시.
4. 미공시 = "공시 없음" / n/13 메타 표기.
5. pure-play vs 그룹 합산 peer 분리 표기.

---

## 자주 발생하는 해석 오류 (Cycle 49 추가)

본 사이트 데이터 해석 시 흔히 발생하는 오류 5가지:

1. **"DMIG 매출 = 73 bn"** ← Note 24 COGS 73 bn과 혼동. **정정**: DMIG FY23 매출 244.99 bn / FY24 253.10 bn (Note 23 PENDAPATAN). Cycle 1 발견.
2. **"KIJA Golf 47.92 bn"** ← curated CSV의 출처 미상 값. **정정**: AR Note 34 직접 추출 85.019 bn. Cycle 5 발견.
3. **"PIPG GP 마진 64.8% 또는 63.4%?"** ← 두 값 모두 정확하지만 다른 metric. **명시**: 64.8% = 전체 P&L GP (총매출/총 COGS) vs 63.4% = Golf course Line GP (Note 27 Golf line / Note 28 Golf line). Cycle 34·35.
4. **"BKDP는 골프 회사"** ← 회사명에 "Darmo Golf"가 있어 혼동. **정정**: BKDP Note 21 매출은 Shopping center 임대 + Apartment + Office 임대. 골프 매출 라인 자체 없음. Cycle 24 발견.
5. **"SMDM Golf FY22 75.6 bn"** ← curated CSV. **정정**: AR FY23 AR p.212 직접 추출 51.66 bn. Cycle 10 발견.

→ 모든 정정 사례 = [CORRECTIONS.md](CORRECTIONS.md) 11건.

## 진행 중

본 사이트는 사이클 단위 무한 개선 루프 (사용자 Stop 시까지).
Cycle 1-57 누적: 7 페이지 (index·overview·unit-economics·revenue·cost-hr·assets·risk) / 6 메타 문서 / 8 데이터 JSON / 22+ 시각화 / 10 정정 / 6 한계 카테고리.
6 peer (DMIG·PIPG·GOLF·MDLN·KIJA·SMDM) Golf segment AR 직접 추출 + KIJA·SMDM 5 segment OpInc 분포 + DMIG vs PIPG 인력 집약도 비교 + 7 peer 미공시 분류.
다음 사이클 작업은 `IMPROVEMENT_LOG.md` 마지막 "미완 / Cycle N+1 작업" 섹션 참조.
