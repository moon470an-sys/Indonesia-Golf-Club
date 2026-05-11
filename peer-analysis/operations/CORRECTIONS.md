# 운영 벤치마크 — AR 직접 검증 정정 이력

> **메타 문서 cross-reference**: [README.md](README.md) · [IMPROVEMENT_LOG.md](IMPROVEMENT_LOG.md) · [verification_log.md](verification_log.md) · CORRECTIONS.md (본 문서, 11건 정정) · [LIMITATIONS.md](LIMITATIONS.md) · [INVENTORY.md](INVENTORY.md)

curated CSV / 큐레이션 데이터 vs AR Note 직접 추출 정정 사항을 누적 기록.
모든 정정은 AR 페이지/Note 출처 명시.

---

## 매출 수치 정정

### DMIG FY2024 매출 (Cycle 1 검출)
- **before (기존 site/cost-hr.html Cycle 0):** "DMIG FY23 매출 74.29 bn" 표기 (실제 COGS Jumlah 값)
- **after (AR-direct):** DMIG FY23 매출 = **Rp 244,986,267,834** / FY24 = **Rp 253,102,440,194**
- 출처: DMIG FY23 AR p.89 Note 23 / FY24 AR p.86 Note 23
- 영향: revenue.html · unit-economics.html · cost-hr.html 모두 갱신

### DMIG FY2023 net profit (Cycle 1)
- **before (curated peer_financials.csv):** Rp 18,770,741,640 (≈ 18.77 bn) — 잘못된 값
- **after (AR-direct):** Rp 71,268,571,841 (FY24 AR p.52 Income Statement comparative) — BoD report (FY23 AR p.4) Rp 71.26 bn과 일치
- 출처: DMIG FY24 AR p.52 LABA NETO / DMIG FY23 AR p.2 BoD Report
- 영향: cost-hr.html · unit-economics.html 다년 추이

### KIJA Golf segment FY2024 (Cycle 5)
- **before (curated peer_financials_curated.csv):** "KIJA Pure Golf segment FY24 Rp 47.92 bn"
- **after (AR-direct):** Rp **85,019,000,000** (Note 34 Golf segment 표)
- 출처: KIJA FY24 AR att1 p.523-524 Note 34 INFORMASI SEGMEN
- 영향: revenue.html · cost-hr.html · unit-economics.html
- 비고: curated 47.92 bn 출처 추적 불가. AR 직접 추출이 정확.

### SMDM Golf & Country Club segment FY2024 (Cycle 6 + Cycle 10 보강)
- **before (curated):** "SMDM Golf+CC FY22 Rp 75.6 bn (13.4% of net sales)"
- **after (AR-direct):** FY22 Rp **51,663 m** / FY23 Rp 58,197 m / FY24 Rp 63,282 m. 3-yr CAGR +10.7%.
- 출처: FY24 AR att1 p.219-220 Note 29 (FY23·FY24) + FY23 AR att1 p.212 Note 29 (FY22 comparative column)
- 영향: revenue.html · cost-hr.html · unit-economics.html · data/smdm_notes.json (FY22 추가)
- 비고: curated 75.6 bn은 Golf+Estate Mgmt 합계(약 71.15 bn) 또는 다른 정의 추정. AR-direct Golf만 51.66 bn.
- 추가 발견: GP 마진 FY22 54.8% / FY23 55.8% / FY24 38.9% — FY24 큰 하락 (-15.9pp 누적).

### KPIG "Trump Lido membership 7.36 bn" (Cycle 7)
- **before (curated):** "KPIG Golf membership FY24 Rp 7.36 bn (Trump Lido 1년차)"
- **after (AR-direct):** AR Note 31에서 Golf 단독 라인 없음. "Hotel, resor dan golf" 통합 Rp 960.227 bn으로만 표기.
- 출처: KPIG FY24 AR att1 p.315 Note 31 PENDAPATAN USAHA
- 영향: revenue.html · 골프 단독 GP 비교에 KPIG 제외
- 비고: 7.36 bn은 다른 sub-disclosure에서 가능하나 본 사이트는 AR Note 직접 검증 가능한 값만 게재.

---

## 자산·시설 수치 정정

### GOLF 코스 구성 (Cycle 3)
- **before (curated):** "GOLF Black Rocks Belitung 48.07% 자회사"
- **after (AR-direct):** GOLF는 3개 골프장 운영: NKG (Pecatu Bali, subsidiary) + SGU (Palm Hill Sentul, subsidiary) + BGR (Black Rocks Belitung, **entitas asosiasi** — 비연결). 매출 197,994 bn은 연결만 (NKG+SGU+SBP), BGR는 equity method.
- 출처: GOLF FY24 AR p.62 Wilayah Operasional + p.189 PT Belitung Golf and Resorts (Other receivables) + p.212 Note 34 Pihak Berelasi
- 영향: assets.html · unit-economics.html · revenue.html에서 GOLF 코스 수 36 (연결) / 54 (BGR 포함 참고)로 분리 표기
- 비고: 48.07% 지분율 정량 확인은 Cycle 9에서도 ownership table 직접 추출 미완.

### DMIG 코스 면적·홀 수 (Cycle 1)
- **before (curated):** 일부 불명
- **after (AR-direct):** BSD Course 18 hole 76 ha (Jack Nicklaus 설계) + PIK Course 18 hole 80 ha (Robert Trent Jones Jr 설계) = 36 hole 156 ha
- 출처: DMIG FY24 AR p.5 Profil Perusahaan
- 정규직 198명 (BSD 100 + PIK 98) FY24, FY23 207명 (BSD 112 + PIK 95)
- 출처: DMIG FY24 AR p.19 SDM Tabel 6

### PIPG 코스 면적·홀 수 (Cycle 2)
- **before (curated):** 일부 불명
- **after (AR-direct):** 18 hole 530,095 m² (53.01 ha), 12 land certificates. HGB 209,533 m² 만료 2025·2055년 + Hak Pakai 40,319 m².
- 출처: PIPG FY24 AR p.7 Profil + p.131 Note 10 + p.132 Note 12
- 정규직 254명 FY24 (Cycle 8)
- 출처: PIPG FY24 AR p.74 SDM

---

## 매출 집중 / 매입 집중 정정 (Cycle 3-4)

### GOLF 매출 단일 고객 집중
- AR-direct: PT Triniti Garam Properti FY24 Rp 67.856 bn = **34%** of total revenue (FY23 25%)
- 출처: GOLF FY24 AR p.211 Note 29 (continued)
- 영향: risk.html 매출 집중 위험 표 (Cycle 3 신규 섹션)

### MDLN 매입 단일 공급사 집중
- AR-direct: PT Jumbo Power International FY24 Rp 62.020 bn = "melebihi 10%" of total COGS
- 출처: MDLN FY24 AR att2 p.319 Note 26 (continued)
- 영향: risk.html 매입 집중 위험 표 (Cycle 4 신규 섹션)

### MDLN FY2023 net loss (Cycle 12 신규 발견)
- **before (curated):** FY24 net loss -690.3 bn만 표기 (FY23 net profit/loss 미수집)
- **after (AR-direct):** FY23 net loss attributable to parent = Rp **101,974,457,012** (= -102 bn). FY24 -690.27 bn. **MDLN은 2년 연속 적자**.
- 출처: MDLN FY24 AR att2 p.204 Exhibit B/2 Income Statement comparative
- 영향: risk.html 손실·적자 공시 표 강조, 누적 2년 손실 ≈ Rp 792 bn

### BKDP Going Concern 강조 (Cycle 12 신규)
- **before (curated):** FY24 net loss -35.9 bn만 표기. 감사의견 미수집.
- **after (AR-direct):** Auditor's Report에 명시적 "Kelangsungan Usaha (Going Concern)" 불확실성 paragraf. 누적 손실 Rp 493,279,152,383 명시. Opini 자체는 "tidak dimodifikasi" (적정의견 유지).
- 출처: BKDP FY24 AR att2 p.57 Laporan Auditor Independen No. 00092/2.1138/AU.1/05/1375-4/1/III/2025
- 영향: risk.html 손실 표 강조 + 감사의견 표 BKDP row 채움 (Cycle 12 첫 audit opinion AR-cited 사례)

### BKDP 매출 구성 = 골프 X, 쇼핑센터 임대 위주 (Cycle 24 신규 발견)
- **before (curated 가정):** "Bukit Darmo Golf" 운영 가정
- **after (AR-direct):** Note 21 PENDAPATAN USAHA FY24 = 쇼핑센터 임대 Rp 6.84 bn + Apartment 임대 0.74 bn + Office building 임대 0.17 bn + 기타 (총 30.5 bn). **골프 매출 라인 없음**. Note 22 직접 비용도 "Pusat Perbelanjaan (Shopping Centers)" 전용 (Penyusutan 20.11 + PBB 4.24 + Listrik 11.82 + Perbaikan 0.61 + Kebersihan 0.98 = 37.76 bn).
- 출처: BKDP FY24 AR att2 p.118-119 Note 21·22
- 영향: 본 사이트 BKDP 포지셔닝 정정 — "Bukit Darmo Property"는 쇼핑센터 + 부동산 임대 사업, 골프 운영은 그룹 외 (curated의 "Bukit Darmo Golf" 운영자 = 별도 entity 추정). BKDP 적자도 골프 사업 적자가 아닌 부동산 사업 적자.

---

## 토지권 만료년 공시 사례 (Cycle 2)

### PIPG HGB 만료 (Cycle 2 첫 사례)
- AR-direct: HGB 209,533 m² 만료 2025년 및 2055년 (2 batch)
- 출처: PIPG FY24 AR p.131 Note 10 INVESTMENT PROPERTY ("Tanah dengan status HGB ... akan berakhir pada tahun 2025 dan 2055")
- 영향: risk.html 토지권 표 (Cycle 2 첫 AR-cited row)

---

## 회원권 정책 정성 공시 (Cycle 1)

### DMIG Refundable Membership Fee
- AR-direct: "Refundable membership fee may be paid in full amount or installment payment."
- 출처: DMIG FY23 AR p.86 Note 18
- 영향: revenue.html 회원권 모델 표 + risk.html 회원권 운영 이슈

---

## 매출 집중 / 후속사건 (Cycle 1, Cycle 3)

### SMDM 인수 (Cycle 1, 후속사건)
- AR-direct: SMDM 91.99% acquired by BSDE (Sinarmas Land), 2024-10
- 출처: curated peer_financials_curated.csv relationship_note (AR 직접 출처 매핑 Cycle 9 추출 검토)
- 영향: risk.html 후속사건 표

### KPIG 사명 변경 (post-FY24)
- AR-direct (간접): 2025-07 PT MNC Land Tbk → PT MNC Tourism Indonesia Tbk
- 출처: curated peer_financials_curated.csv
- 영향: risk.html 후속사건 + 법인 구조 표

---

## 사이클별 정정 사항 요약

| Cycle | 정정 건수 | 주요 정정 |
|-------|-----------|----------|
| 1 | 2 | DMIG 매출 (COGS와 혼동) / DMIG FY23 net profit |
| 2 | 1 | PIPG land 데이터 (curated 미수집 → AR 추출) |
| 3 | 1 | GOLF 3 courses 분리 (BGR associate) |
| 4 | 0 | MDLN 신규 데이터 (정정 없음 — curated 74.3 bn ≈ AR 74.375 bn 일치) |
| 5 | 1 | KIJA Golf 47.92 → 85.019 bn |
| 6 | 1 | SMDM Golf 75.6 (FY22 curated) → 63.282 bn (FY24 AR) |
| 7 | 1 | KPIG 7.36 bn → AR Note 31에 분리 없음 (단독 라인 X) |
| 8 | 0 | PIPG·SMDM SDM 추출 (신규, 정정 없음) |
| 9 | 0 | CORRECTIONS.md 신규 + 13-peer 매출 visual (신규 데이터, 정정 없음) |
| 10 | 0 | SMDM FY22 보강 (51.66 bn 확정, 정정 없음 — 기존 정정의 검증) |
| 11 | 0 | 회원권 비중 차트 + 매트릭스 SMDM·KIJA 보강 (정정 없음) |
| 12 | 2 | MDLN FY23 손실 -101.97 bn (curated 미수집) + BKDP Going Concern 강조 (curated 누락) |
| 13 | 0 | 6-peer Golf 매출 시계열 + MDLN auditor 한계 명시 |
| 14 | 0 | PIPG·MDLN FY22 추출 (CAGR 검증) |
| 15-22 | 0 | 시각화·meta 문서·footer 일관성 (정정 없음) |
| 23 | 0 | DMIG vs PIPG 인력 집약도 시각화 (정정 없음) |
| 24 | 1 | BKDP 매출 = 쇼핑센터 임대 (골프 운영 없음) curated 정정 |
| 25-85 | 0 | 시각화·meta 문서·FY25 follow-up 추출·milestone retrospective (정정 없음) |
| 86 | 1 | (Self) cost-hr.html FY25 follow-up 작성 중 MDLN FY24 Golf course COGS 라인 fabrication 즉시 정정 (Gaji 17,418→19,250 / Penyusutan 5,043→2,756 / Lain-lain 8,824→9,425 / 합계 31,285→31,431 m). mdln_notes.json 재대조 후 동일 사이클 내 자동 정정. |
| 87-130 | 0 | 13/13 peer 추출 완주 (Cycle 92-103) + 메타 sync + 한계 해소 (정정 없음) |
| 누적 | **11건** | 모두 AR 직접 추출로 보강 |

---

## 검증 표준
- 모든 매출 수치는 income statement + 매출 Note(통상 Note 23 또는 27 또는 25 또는 29)의 **두 출처 일치** 후 게재.
- 모든 비용 수치는 COGS Note + OpEx Note + 매출원가 비율 산출 cross-check.
- 정규직 수는 SDM 섹션 표 직접 인용만 (정성 텍스트는 보강 자료로만 사용).
- "공시 없음" 표기 = AR 전수 검색 후 미발견. (예: KPIG Note 31에 Golf 단독 line 없음.)

본 정정 이력은 매 사이클 새 정정 발생 시 누적 기록.
