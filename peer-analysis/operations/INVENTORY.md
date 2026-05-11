# 운영 벤치마크 — 사이트 산출물 인벤토리

> **메타 문서 cross-reference**: [README.md](README.md) · [IMPROVEMENT_LOG.md](IMPROVEMENT_LOG.md) · [verification_log.md](verification_log.md) · [CORRECTIONS.md](CORRECTIONS.md) · [LIMITATIONS.md](LIMITATIONS.md) · INVENTORY.md (본 문서, 종합 산출물)

본 사이트의 모든 산출물 (페이지·메타 문서·데이터 JSON·차트) 종합 목록.
Cycle 1-57 누적 결과 기준 (마지막 갱신 Cycle 57).

---

## 1. 사이트 페이지 (6개)

| 파일 | 역할 | 주요 섹션 |
|------|------|----------|
| `index.html` | 사이트 entry. 카테고리 5 카드 + 6-peer 톱-레벨 요약 + 13-peer 추출 매트릭스 + 13-peer 운영 분류. | bignum row (13/6/10/31) · cat-grid · 6-peer summary · progress matrix |
| `overview.html` | TLDR 1-screen 요약 (Cycle 31 신규). | 5 핵심 발견 · 6-peer 1-card · 4 한계 박스 |
| `unit-economics.html` | 홀당·ha당·1인당 매출 (Pure-play 우선). | DMIG·PIPG·GOLF 단위 경제 + DMIG vs PIPG 인력 집약도 시각화 |
| `revenue.html` | 매출 믹스 + segment 분리 매트릭스. | DMIG·PIPG·KIJA 100% stacked bar + 13-peer 시각화 + 4-c KIJA segment + 회원권 시계열 |
| `cost-hr.html` | 매출원가·판관비 라인 분해. | DMIG 27라인 + PIPG 38라인 + GOLF 29라인 + MDLN 10라인 + KIJA 4 + SMDM 4 + 6-peer GP/OpInc 시각화 |
| `assets.html` | 시설 정량 + 부속 시설 매출. | AR-cited 코스 정량 표 + DMIG The Range 매출 + 정성 시설 (Phase A) |
| `risk.html` | AR 공시 위험 사례. | 손실 peer + 매출 집중 (GOLF) + 매입 집중 (MDLN) + 회원권 운영 + 토지권 (PIPG) + 감사의견 (BKDP) + 후속사건 |

---

## 2. 메타 문서 (5개)

| 파일 | 역할 |
|------|------|
| `IMPROVEMENT_LOG.md` | 사이클별 변경 누적. Cycle 1-31 history table + 각 cycle 상세 변경 + 미완 작업. |
| `verification_log.md` | 사이클별 페이지 검증 (a:출처 / b:수치 일치 / c:공시 없음 정확성 / d:원칙 위반). |
| `CORRECTIONS.md` | curated CSV → AR-direct 정정 11건 누적 (Cycle 86 self-correction 포함). |
| `LIMITATIONS.md` | 추출 한계 6 카테고리 (이미지 PDF / 회전 표 / 미공시 / curated 미검증 / 시계열 / 정성 정보) + 신뢰 등급 5단계. |
| `INVENTORY.md` (본 문서) | 산출물 종합 inventory (Cycle 32 신규). |

---

## 3. 데이터 JSON (13개 peer + 통합 + 기존 = 15개, data/ 하위) — **13/13 완주 (Cycle 103)**

| 파일 | peer | 내용 |
|------|------|------|
| `dmig_notes.json` | DMIG | Revenue Note 23 (7 라인) + COGS Note 24 (3 라인) + OpEx Note 25 (17 라인) + Related party Note 26 (FY22·FY23·FY24) |
| `pipg_notes.json` | PIPG | profile (18 hole, 53 ha, 12 sertifikat) + Financial Highlights FY22-24 + Revenue Note 27 (11 라인) + COGS Note 28 (10 라인) + OpEx Note 29 (17 라인) + Agreements Note 32 (5건) + Dividends Note 26 |
| `golf_notes.json` | GOLF | courses (3 NKG+SGU 연결 + BGR associate) + Financial Highlights FY22-24 + Revenue Note 29 (4 segment + 고객 집중 Triniti 34%) + COGS Note 30 (4) + Selling Note 31 (5) + G&A Note 32 (16) + **FY25 follow-up** (Cycle 79) |
| `mdln_notes.json` | MDLN | Segment Note 32 (by location 5 + by product 3) + Revenue Note 25 (Lapangan golf 4 sub + 기타) + COGS Note 26 (Golf 3 + F&B 3 + Hotel 5 + 매입 집중 Jumbo Power) + **FY25 follow-up** (Cycle 77) |
| `kija_notes.json` | KIJA | Segment Note 34 Golf segment FY24 (Penjualan 85.0 / BPP -49.6 / GP 35.4 / Sel 1.7 / G&A 28.6 / Net 6.7 bn) + Real Estate segment 정량 + 5-segment FY24 extended + **FY25 cross-validation** (Cycle 80) |
| `smdm_notes.json` | SMDM | Segment Note 29 FY22 (Real Estat + Golf 51.7 + Estat Mgmt + Hotel + Lainnya) + FY23 + FY24 + **FY25 follow-up restatement caveat** (Cycle 78) |
| `kpig_notes.json` | KPIG | Revenue Note 31 (Hotel+resor+golf 통합 X) + G&A Note 34 (13 라인) + EPS Note 35. **Golf 단독 분리 없음** key finding + **FY25 follow-up** (Cycle 80, 회사명 변경 검증) |
| `bkdp_notes.json` | BKDP (Cycle 92 신규) | **FY25 P&L 직접 추출** (Revenue 36.63 bn +20.0% / Gross Loss -5.73 bn / Net Loss -35.57 bn / EPS -4.73) + Going Concern image PDF 한계 명시 |
| `smra_notes.json` | SMRA (Cycle 95 신규) | **FY25 Note 31·32 직접 추출**: Rekreasi/Leisure 매출 61.11 bn (-8.3%) / COGS 54.51 bn / GP 마진 18.0% → 10.8% (-7.2pp). 그룹 총매출 -17.5%. Leisure 통합 라인 — 골프 단독 분리 없음. |
| `bsde_notes.json` | BSDE (Cycle 98 신규) | **FY25 Informasi Segmen 직접 추출 (Cycle 56 실패 해소)**: 5 segment Real Estat·Properti·Hotel·Jalan tol·Lain-lain — **Golf segment 없음 확인**. Consolidated 매출 12,788 bn (-7.3%) / Hotel +193.7% / Jalan tol -85.0% / Op Profit -22.9%. DMIG associate equity는 Lain-lain segment에 통합. |
| `dild_notes.json` | DILD (Cycle 101 신규) | **FY25 Informasi Segmen 직접 추출**: 6 segment Land·High Rise·Industri Perkantoran·Estate Facilities·Hotels·Lainnya — **Golf segment 없음 확인**. Segment results: Land +72.8% / High Rise -49.6% / Hotels +25.9%. Consolidated 자산 12,756 bn. |
| `mkpi_notes.json` | MKPI (Cycle 102 신규) | **FY25 Note 37 Informasi Segmen Usaha 직접 추출**: 6 segment Shopping Center·Office·Apartment·Real Estate·Water Park·Hotel — **Golf segment 없음**. Pondok Indah Golf은 PIPG (associate) 운영. Operating income Rp 1,240 bn / Net Rp 1,122 bn. |
| `bksl_notes.json` | BKSL (Cycle 103 신규 — **13/13 완주**) | **FY25 Note 37 Segmen Operasi 직접 추출**: 2 segment Real Estat(primary) + Lain-lain(restoran·taman hiburan·pengelolaan kota) — **Golf segment 없음 확인**. Sentul Golf은 PT Padang Golf Bukit Sentul (관계사) 운영 (Cycle 24 일관). Net profit Rp 833 bn. |
| `peers_summary.json` | 13 peer 통합 (Cycle 33·81·97·105 regenerate) | 위 13 JSON merge + _meta (peer_count, FY 범위, 출처). **Cycle 105 79.0 KB (13/13 완주 — BSDE·DILD·MKPI·BKSL 추가)**. downstream consumer가 단일 파일로 query 가능. |

**JSON 파일 크기 분포 (Cycle 143 audit)**:
- 가장 큰 peer JSON: pipg_notes.json (8.9 KB) — Pure-play golf, Note 27·28·29 + 5 agreements + HGB 토지권 + SDM 254명
- 가장 작은 peer JSON: smra_notes.json (2.1 KB) — Leisure 통합 라인 1개 + Note 32 1줄
- 평균 peer JSON: 4.5 KB (Pure-play / Hotel·Golf 통합 peer가 큼, segment 1줄 peer가 작음)
- 13 peer notes 총합: 58.0 KB, peers_summary.json: 79.0 KB (포함된 데이터의 superset)

---

## 4. 핵심 시각화 (Cycle 누적)

| 시각화 | 위치 | 사이클 |
|--------|------|--------|
| DMIG 매출 100% stacked bar (FY22-24) | revenue.html section 2 | Cycle 1 |
| PIPG 매출 100% stacked bar (FY22-24) | revenue.html section 2-b | Cycle 2 |
| 13-peer 그룹 매출 분포 (linear bar) | revenue.html section 5 | Cycle 9 |
| 13-peer 추출 진행 매트릭스 (143 cells 색상) | index.html | Cycle 15 |
| 6-peer Golf GP 마진 horizontal bar | cost-hr.html | Cycle 6 |
| 6-peer Golf GP YoY 변화 표 (FY23→FY24) | cost-hr.html | Cycle 7 |
| Golf 영업이익률 + 매출원가율 FY22-24 시계열 표 | cost-hr.html | Cycle 18 |
| 6-peer GP vs OpInc 짝지은 시각화 | cost-hr.html | Cycle 20 |
| DMIG vs PIPG 인력 집약도 4-paired bar | unit-economics.html | Cycle 23 |
| 6-peer Golf 매출 3-yr 시계열 | revenue.html section 4-b | Cycle 13-14 |
| KIJA 5-segment 분포 (Real Estat dominant) | revenue.html section 4-c | Cycle 26 |
| 13-peer 운영 분류 표 (7 유형) | index.html | Cycle 25 |
| 6-peer 톱-레벨 ratio 요약 | index.html | Cycle 19 |
| TLDR 6 peer 1-card | overview.html | Cycle 31 |
| KIJA 5-segment GP 마진 horizontal bar | revenue.html section 4-c+ | Cycle 38 |
| SMDM 5-segment GP 마진 horizontal bar | revenue.html section 4-c+ | Cycle 39 |
| GOLF 4-segment GP 마진 horizontal bar | revenue.html section 4-c+ | Cycle 40 |
| DMIG 7-라인 GP 마진 table | revenue.html section 4-c+ | Cycle 42 |
| PIPG 11-라인 GP 마진 table | revenue.html section 4-c+ | Cycle 42 |
| FY25 follow-up 매출 표 (5 peer + DMIG·PIPG 미가용) | revenue.html section 5 | Cycle 84 |
| FY25 follow-up MDLN Golf course COGS 4행 표 (+104.1% Penyusutan) | cost-hr.html | Cycle 86 |
| **FY24→FY25 paired bar 시각화 (5 peer)** | revenue.html section 5+ | **Cycle 159** |

**시각화 총 25 개** (Cycle 162 종료). 위치별 분포: revenue.html 14 / cost-hr.html 6 / unit-economics.html 3 / index.html 2 / overview.html (TLDR 카드).

---

## 5. AR 직접 추출 페이지 인용 (검증 sources)

### DMIG FY24 AR (102 pages)
- p.5 Profil Perusahaan (2 courses 36 hole 156 ha)
- p.19 SDM Tabel 6 (정규직 198명)
- p.52 Laporan Laba Rugi (net 82,404,512,711)
- p.86 Note 23 매출 7 라인 + Note 24 COGS 3 라인
- p.87 Note 25 OpEx 17 라인 + Note 26 핵심경영진 급여
- p.88 Note 27 Perpajakan
- p.42-49 Auditor's Report (**image-based, 추출 불가**)

### PIPG FY24 AR (155 pages)
- p.7 Profil (18 hole 530,095 m² 12 certificates)
- p.11 Ikhtisar Keuangan (FY22-24 종합)
- p.74 SDM (254명)
- p.91 Income Statement
- p.131 Note 10 HGB (209,533 m² 만료 2025·2055)
- p.132 Note 11 RoU (MKPI 임차) + Note 12 deferred land
- p.141 Note 27 매출 11 라인
- p.142 Note 28 COGS 10 + Note 29 OpEx 17
- p.143 Note 32 Agreements (5건)

### GOLF FY24 AR (224 pages)
- p.10 Ikhtisar (FY22-24)
- p.62 Wilayah Operasional (3 courses + areas)
- p.160 Income Statement
- p.210 Note 29 (4 segment + 고객 집중)
- p.211 Note 30 (COGS 4) + Note 31 (Selling 5)
- p.212 Note 32 G&A 16

### MDLN FY24 AR (att1 88p + att2 351p)
- att2 p.204 Income Statement (FY24 net -690.3 + FY23 -102 bn)
- att2 p.318 Note 25 Revenue
- att2 p.319 Note 26 COGS (Golf 3 + F&B 3 + Hotel 5 + 매입 집중 Jumbo Power)
- att2 p.323-324 Note 32 segment (by location + by product)
- att2 p.200-202 Auditor's Report (**image-based, 추출 불가**)

### KIJA FY24 AR att1 (554 pages)
- p.520 Note 31 Financial Expenses + Note 32 Other
- p.523-524 Note 34 5-segment (Real Estat + Golf + Listrik + Town Mgmt + Pariwisata)

### SMDM FY24 AR att1 (230 pages)
- p.54 SDM (그룹 665명)
- p.219-220 Note 29 Segment (Real Estat + Golf&CC + Estat + Investasi + Lainnya)
- p.221 관계자 거래

### BKDP FY24 AR att2 (138 pages)
- p.57 Auditor's Report (**Going Concern 명시**)
- p.118-119 Note 21 매출 (Mall+Apartment+Office) + Note 22 직접비

### KPIG FY24 AR att1 (334 pages)
- p.315 Note 31 매출 (Hotel+resor+골프 통합 — Golf 분리 없음)
- p.316 Note 34 G&A 13 라인

### FY23 AR 추가 추출 (FY22 comparative)
- PIPG FY23 AR p.143 Note 27 (FY22 sub-line)
- MDLN FY23 AR att1 p.315 Note 25 (FY22 sub-line)
- SMDM FY23 AR att1 p.211-212 Note 29 (FY22)

---

## 6. 한계 카테고리 별 영향 peer

| 한계 | 카테고리 | 영향 peer |
|------|----------|-----------|
| 이미지 PDF | LIMITATIONS 1 | DMIG audit · MDLN audit · 기타 추정 |
| 회전 표 | LIMITATIONS 2 | KIJA Note 34 (FY22-FY23 부분만) |
| AR 분리 미공시 | LIMITATIONS 3 | KPIG · BSDE · BKSL · SMRA · DILD · BKDP · MKPI (7) |
| curated 미검증 | LIMITATIONS 4 | KIJA 47.92 bn (CORRECTIONS 5) · SMDM 75.6 bn (CORRECTIONS 6) · KPIG 7.36 bn (CORRECTIONS 7) · GOLF BGR 48.07% |
| FY22 시계열 부분 | LIMITATIONS 5 | GOLF (IPO 후) · KIJA (회전 표) |
| 정성 정보 | LIMITATIONS 6 | 회원권 단가·연회비·회원 수 (13 peer 0건) |

---

## 7. Cycle 카테고리 분포

| 카테고리 | Cycle (총 31) |
|----------|---------------|
| 신규 peer AR 직접 추출 | 1·2·3·4·5·6·7·10·12·14·24 (11 cycle) |
| 신규 시각화 | 6·9·11·13·17·19·20·22·23·26·31 (11) |
| 신규 메타 문서 | 1 (IMPROVEMENT/verification) · 9 (CORRECTIONS) · 21 (LIMITATIONS) · 32 (INVENTORY) |
| Placeholder cleanup | 27·28·29·30 (4) |
| 사이트 일관성·footer | 22 (1) |
| 추출 한계 명시 | 13·16·21 |
| 정정 (CORRECTIONS) | 1·5·6·7·12·24·86 (총 11건) |

---

## 8. 운영 총괄을 위한 사용 가이드

1. **첫 방문**: `overview.html` TLDR → 5 핵심 발견 + 6 peer 1-card 한 화면.
2. **deep dive**: `index.html` 5 카테고리 카드에서 관심 영역 선택.
3. **데이터 정확성 확인**: 페이지의 모든 수치는 AR 페이지/Note 인라인 인용. `CORRECTIONS.md`에서 curated 정정 사례 확인.
4. **한계 인지**: `LIMITATIONS.md` 추출 한계 6 카테고리 — 어떤 데이터가 본 사이트에 없는지 명시.
5. **사이클 추적**: `IMPROVEMENT_LOG.md` 사이클별 변경 history.

본 사이트는 144+ 사이클 누적 결과 (Cycle 1-144). 새로운 데이터·시각화는 IMPROVEMENT_LOG.md에 사이클 단위 추가.

---

## 9. 사이트 자산 정량 (Cycle 145 audit)

| 카테고리 | 파일 수 | 총 크기 | 총 라인 |
|----------|---------|---------|---------|
| HTML 페이지 | 7 | 336.3 KB | 5,554 |
| 메타 문서 | 6 | 251.7 KB | 3,913 |
| 데이터 JSON | 15 (13 peer + summary + 기존) | 149.0 KB | — |
| **합계** | **28 파일** | **~737 KB** | **9,467+** |

**가장 큰 단일 파일**:
- HTML: cost-hr.html (104.8 KB, 1,881 lines) — 13-peer 운영비 분해 + 6-peer GP/OpInc 시각화
- 메타: IMPROVEMENT_LOG.md (187.1 KB, 2,837 lines) — 144 cycle 변경 history + 상세 entry
- 데이터: peers_summary.json (79.0 KB) — 13 peer 통합 single source

본 사이트 144 cycle 누적 결과의 정량 footprint. 100+ cycle 누적 work의 visible artifact.
