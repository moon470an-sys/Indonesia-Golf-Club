# 운영 벤치마크 — AR 추출 한계 명시

> **메타 문서 cross-reference**: [README.md](README.md) · [IMPROVEMENT_LOG.md](IMPROVEMENT_LOG.md) · [verification_log.md](verification_log.md) · [CORRECTIONS.md](CORRECTIONS.md) · LIMITATIONS.md (본 문서, 6 카테고리) · [INVENTORY.md](INVENTORY.md)

본 사이트는 IDX 13 peer의 공식 AR 텍스트-PDF 직접 추출에 한정한다.
이미지 기반 PDF, 회전 표, AR 외부 출처(curated CSV) 등은 한계로 명시한다.

**한계 해소 사례 #2 (Cycle 167)**: DMIG·PIPG FY2025 AR이 IDX/사이트 환경에 부재 (LIMITATIONS 5 FY 시계열 부분 누락) → 각 peer 공식 IR 사이트 직접 다운로드로 해소. damaiindahgolf.com + golfpondokindah.com에서 FY25 AR + Financial Statement att2 확보. 13/13 peer FY22-FY25 4년 series 완성. PDF 부재로 인한 시계열 단절 첫 해소 사례.

**한계 해소 사례 #3 (Cycle 168) — Peer Group 분류 자체 재편**: 일부 peer (MKPI·BKDP·BKSL·DILD)가 LIMITATIONS cat.3 (AR 분리 미공시)에 속해 분석 가치 낮음 → Peer Group v2로 4 swap. 제거된 4 peer는 `operations/data/archived/`에 보존 (history). 신규 추가 4 peer (CTRA·ELTY·LPKR·PWON)는 운영 골프장 직접 보유한 부동산 그룹. **결과**: 골프 운영 정보 0 peer가 1 → 0으로 감소. AR 분리 미공시 한계가 framework 차원에서 부분 해소 (분석 우선순위 명확화).

**한계 해소 사례 (Cycle 56 → 98)**: BSDE FY24 AR att2 segment Note 추출 실패 (Cycle 56) → BSDE FY25 AR에서 동일 Note 텍스트 추출 성공 (Cycle 98). 일부 image-PDF 추정 한계는 후속 fiscal year AR에서 해소 가능함을 입증.

---

## 1. 이미지 기반 PDF (텍스트 추출 불가)

PyMuPDF 텍스트 추출 시 빈 문자열 반환 → 이미지 OCR 별도 작업 필요.

### DMIG FY2024 AR — Auditor's Report (p.42-49)
- **상태:** 이미지 임베드, 텍스트 비어 있음
- **결과:** DMIG audit opinion AR-cited 추출 불가
- **대안:** OCR (Tesseract / Cloud Vision) 별도 작업 또는 직접 PDF 뷰어 확인

### MDLN FY2024 AR att2 — Auditor's Report (p.200-202)
- **상태:** 이미지 임베드, 텍스트 비어 있음
- **결과:** MDLN audit opinion AR-cited 추출 불가
- **중요성:** MDLN은 FY23·FY24 2년 연속 적자 (각 -102 bn / -690 bn). Going Concern 여부 미확인 = 핵심 risk 정보 누락.

### 기타 peer auditor's report
- PIPG·GOLF·KIJA·SMDM·KPIG·BSDE·BKSL·SMRA·DILD·MKPI — 모두 Cycle 21 시점 추출 미완. BKDP만 텍스트 기반 ✓ (Cycle 12 완료).

---

## 2. 회전 표 (column-aware 추출 부분 성공)

KIJA의 segment information table은 90° 회전되어 PyMuPDF 기본 x-y 정렬과 어긋남.

### KIJA FY2024 AR att1 p.524 Note 34
- **추출 성공 (Cycle 16):** FY24 Golf segment 9 P&L 라인 모두 정량 (Penjualan 85.019 / BPP -49.634 / Laba bruto 35.385 / Sel -1.665 / G&A -28.604 / 기타) — column-aware 재추출로 검증.
- **추출 미완:** FY24 Real Estat·Listrik·Town Mgmt·Lain-lain 4 segment 동일 9 라인 (회전 표 동일 구조).

### KIJA FY2023 AR att1 p.413-415 Note 34
- **상태:** FY22-FY23 segment 데이터, 회전 표 + 다중 fiscal year × 다중 segment
- **결과:** Cycle 16에서 일부 텍스트 추출 시도하였으나 행/열 매핑 어려움. 정확 추출 미완.

---

## 3. AR Note 분리 미공시 (구조적 한계)

이미지/회전이 아닌 **AR 자체에 골프 단독 라인이 없는** 경우.

### KPIG (PT MNC Tourism Indonesia)
- **Note 31 Pendapatan Usaha**: "Hotel, resor dan golf" 통합 라인 Rp 960.227 bn 단일. Golf 단독 분리 없음.
- **결과:** KPIG는 6-peer Golf 비교 대상 외. curated "Trump Lido membership 7.36 bn" 출처 미확인.

### BSDE
- DMIG associate 합산만. Golf 단독 매출·자산 별도 분리 없음.
- Cycle 56 추가 검증: BSDE FY24 AR att2 (490 pages) segment Note text-PDF 추출 실패 (image-based 가능성 또는 별도 형식).
- **Cycle 98 일부 해소**: BSDE FY25 AR att2 p.491 Informasi Segmen Operasi 직접 추출 성공. 5 segments: Real Estat·Properti·Hotel·Jalan tol·Lain-lain — **Golf segment 없음 확인** (FY25 + FY24 comparative 일관). Cycle 56 image-PDF 추정은 일부 페이지에 국한된 것으로 추정 (FY25 AR same Note 텍스트 추출 가능). data/bsde_notes.json (Cycle 98).

### BKSL
- Sentul Golf은 PT Padang Golf Bukit Sentul (관계사) 운영. BKSL 직접 매출에 포함되지 않음.
- **Cycle 103 추가 검증**: BKSL FY25 AR att1 p.299 Note 37 Segmen Operasi 직접 추출. 2 segments: Real Estat (primary) + Lain-lain (restaurant, amusement park, town mgmt). **Golf segment 없음 확인** (Cycle 24 finding 일관). FY25 Real Estat 매출 Rp 2,490 bn / Net profit 그룹 Rp 833 bn. data/bksl_notes.json (Cycle 103).

### DILD (Cycle 101 추가 검증)
- **FY25 AR att2 p.445 Informasi Segmen Operasi 직접 추출 (Cycle 101)**: 6 segments — Kawasan Perumahan (Land) · High Rise · Industri Perkantoran · Estate Facilities · Hotels · Lainnya. **Golf segment 없음 확인** (FY25 + FY24 comparative 일관). 그룹 매출 -7.3% / Land segment result +72.8% / High Rise -49.6%. data/dild_notes.json (Cycle 101).

### SMRA / DILD (오리지널)
- Leisure & Hospitality / 부동산 segment 통합. Golf 단독 라인 없음.

### BKDP
- 매출 30.5 bn 라인별 분해 미공시 (전체 그룹 단일). Going Concern 명시 (Cycle 12).

### MKPI
- 직접 골프 운영 없음 (PIPG associate 0.38%만).
- **Cycle 102 추가 검증**: MKPI FY25 AR att1 p.223 Note 37 Informasi Segmen Usaha 직접 추출. 6 segments — Pusat Perbelanjaan · Perkantoran · Apartemen · Real Estat · Taman Air · Hotel. **Golf segment 없음 확인**. Operating income Rp 1,240 bn / Net income Rp 1,122 bn / Total assets Rp 9,464 bn. MKPI는 부동산 관리/임대 그룹 — 골프는 PIPG (associate)에서 운영. data/mkpi_notes.json (Cycle 102).

---

## 4. curated CSV 출처 미확인 항목

`raw_peer_data/peer_financials_curated.csv` 일부 값이 AR Note 직접 추출과 불일치하거나 출처 추적 불가.

### KIJA Golf segment FY24
- **curated:** Rp 47.92 bn (Pure Golf)
- **AR-direct (Cycle 5):** Rp 85.019 bn (Note 34 Golf segment)
- **불일치 원인:** curated 출처 추적 불가. AR-direct 사용.

### SMDM Golf FY22
- **curated:** Rp 75.6 bn (13.4% of net sales)
- **AR-direct (Cycle 10):** Rp 51.66 bn (Note 29 Golf&CC segment)
- **불일치 원인:** curated에 Golf+Estate Mgmt 합산(약 71 bn) 또는 다른 정의로 추정.

### KPIG Trump Lido membership FY24
- **curated:** Rp 7.36 bn (Trump Lido 1년차)
- **AR Note 31 검증:** Note 31에 Golf 단독 라인 없음. Hotel+Resort+Golf 통합 960 bn만 표기.
- **결과:** curated 7.36 bn 출처 별도 search 필요. 본 사이트 미포함.

### GOLF Belitung subsidiary % 
- **curated:** "Belitung 48.07% subsidiary"
- **AR-direct:** FY24 AR p.62 "Entitas asosiasi" 명시 (즉 ≤50%, 비연결). 48.07% 정확 검증은 ownership table 추출 미완.

---

## 5. 시계열 추출 한계

### GOLF FY22 segment 데이터
- FY24 AR Ikhtisar (p.10)에 FY22 그룹 총매출 (111.63 bn)만 있고, Note 29 segment 분해는 FY23-FY24만.
- GOLF는 IPO 2024-07-08 후 첫 AR — FY22-FY23은 IPO Prospectus 또는 BEI 공시 별도 추출 필요.

### MDLN FY22 Golf+F&B COGS
- FY23 AR att1 p.315 Note 25 (매출만) Cycle 14 추출. Note 26 (COGS) FY22 sub-line은 별도 추출 미완.

### 그 외 시계열 미완
- KIJA FY22-FY23 segment 시계열 (회전 표)
- KPIG·BSDE·BKSL·SMRA·DILD·BKDP·MKPI Golf 라인 자체 미공시

---

## 6. 정성 정보 추출 한계

회원권 단가·연회비·회원 수 등 운영 정성 정보의 AR 공시 부족.

### 회원권 단가/연회비
- DMIG: Refundable membership fee 정성 공시 (FY23 AR p.86 Note 18). 단가 미공시.
- PIPG: Iuran keanggotaan dan pendaftaran 매출 라인만. 단가 미공시.
- SMDM: Private + Trial + MAP 카테고리만 정성. 단가 미공시.
- 기타 10 peer: 모두 미공시.

### 회원 수 정량
- 13 peer 중 0/13 AR 정량 공시 (SMRA "800+" 정성만, curated).

### 캐디·외주 인력
- 13 peer 중 0/13 정량 분리. DMIG·PIPG 정규직(198명/254명)에 캐디 포함 여부 미확인.

---

## 7. 본 사이트 데이터 신뢰 등급

| 등급 | 정의 | 본 사이트 표시 |
|------|------|---------------|
| **A (AR-direct)** | AR Note 또는 income statement 직접 추출, 다중 cross-check | 녹색 ✓ + 페이지/Note 번호 인라인 |
| **B (AR comparative)** | FY23 또는 FY24 AR의 comparative column 추출 | 녹색 ✓ + "(FY23 AR comparative)" 명시 |
| **C (curated, AR 미검증)** | curated CSV 출처 그대로 사용, AR 직접 검증 미완 | "(curated)" 표기 |
| **D (정정됨)** | curated와 AR-direct 불일치 → AR-direct로 정정 | CORRECTIONS.md 인용 + 정정 사유 명시 |
| **N/A** | 분리 공시 없음 또는 AR 미공시 | "공시 없음" / "미공시" / "N/A" |

**현재 추출 셀 분포 (Cycle 20 종료, 약 13×11 = 143 셀):**
- A 등급: ~30 셀
- B 등급: ~5 셀
- C 등급: ~15 셀 (총자산, 일부 매출 등)
- D 등급: 9 셀 (CORRECTIONS.md)
- N/A: ~84 셀

**13/13 peer 추출 완주 후 갱신 (Cycle 103·105 시점):**
- **AR 직접 추출 peer**: 13/13 모두 텍스트 기반 검증 (단, Golf segment 분리 공시는 6 peer만).
- **추가 추출 6 peer (Cycle 92-103)**: BKDP (P&L 정량) / SMRA (Note 31·32 Leisure) / BSDE·DILD·MKPI·BKSL (Segment Note 정량) — 모두 A 등급 (AR-direct).
- D 등급 (정정): 9 → 11 (Cycle 12 BKDP Going Concern + Cycle 86 self-correction MDLN COGS 라인 추가).
- N/A 셀 일부 감소: BSDE Cycle 56 N/A → A 등급 (Cycle 98 segment 추출).

---

## 8. 한계 극복 방안 (Cycle 32 보강)

### 8-1. 이미지 PDF (LIMITATIONS 1) — OCR
**도구**: Tesseract OCR (`pytesseract` Python) / Google Cloud Vision API / Azure Form Recognizer / AWS Textract.
**대상 우선순위**:
1. MDLN FY24 AR att2 p.200-202 (2년 연속 적자 -792 bn — Going Concern 여부 확인 가장 시급).
2. DMIG FY24 AR p.42-49 (감사의견 + Emphasis of Matter 여부).
3. 나머지 5 peer auditor's report (GOLF·PIPG·KIJA·SMDM·KPIG).
**검증 절차**: OCR 결과 → 수치 cross-check (이미 AR Note에서 알고 있는 수치) → 텍스트 정확성 확인.

### 8-2. 회전 표 (LIMITATIONS 2) — column-aware extraction
**도구**: `pdfplumber` extract_tables() with custom column detection / `camelot` lattice 모드 / `tabula-py`.
**KIJA FY23 AR Note 34 (p.413-415)**: 9 P&L × 6 segment × 2 fy = 108 셀.
**접근법**: PDF page rotation 90° 적용 후 표 추출 → x·y 좌표를 다시 보정.

### 8-3. AR 분리 미공시 (LIMITATIONS 3) — 외부 source
**대상**: KPIG·BSDE·BKSL·SMRA·DILD·BKDP·MKPI Golf 단독 매출.
**대안 source**:
- BEI 공시 (idx.co.id) 추가 disclosure
- 회사 IR 페이지·Investor Presentation
- 금융감독원 (OJK) 공시 시스템
- 회사 별도 Sustainability Report
**현실적 평가**: 7 peer 모두 AR에 골프 단독 라인 의도적 미공시 → 외부 source에서도 분리 어려움.

### 8-4. curated CSV 출처 미검증 (LIMITATIONS 4) — raw_peer_data 추적
**대상**: KIJA 47.92 / SMDM 75.6 / KPIG 7.36 등 출처 추적 불가 값.
**도구**: raw_peer_data/PHASE_A_SUMMARY.md / raw_peer_data/PHASE_B_SUMMARY.md / raw_peer_data/PHASE_C_SUMMARY.md 검토.
**현재 진행**: Cycle 5·6·7에서 AR-direct 값으로 정정 → CORRECTIONS.md에 기록. curated 원천 추적은 별도 Phase A·B·C 큐레이션 기록 검토.

### 8-5. FY22 시계열 부분 (LIMITATIONS 5) — 추가 AR 추출
**GOLF FY22 segment**:
- GOLF는 IPO 2024-07-08. FY22 단독 AR 없음.
- 대안: **GOLF IPO Prospectus** (E-IPO 또는 BEI 공시), FY22 audited financials.
**KIJA FY22-FY23 Golf segment**:
- KIJA FY23 AR att1 p.413-415 회전 표 — column-aware 재추출 (8-2와 동일).

### 8-6. 정성 정보 (LIMITATIONS 6) — peer별 별도 disclosure
**회원권 단가/연회비**:
- AR에 정량 없음 (13 peer 모두). 회원 모집 시 contact-only.
- 대안: peer 홈페이지 회원권 page · IR 자료.
**회원 수 정량**:
- DMIG·PIPG·SMDM Profil section에 카테고리 (Refundable / Trial / MAP)만 명시 → 수 자체 없음.
- 대안: 회사 별도 disclosure 또는 회원권 약관.
**캐디 인원**:
- SDM Tabel은 정규직만. 캐디는 외주·일용 (인도네시아 일반).
- 대안: AR Sustainability Report 또는 Profil의 별도 언급.

---

## 9. 한계 극복 후 예상 사이트 변화 (Cycle 32+)

이미지 PDF audit + 회전 표 + FY22 시계열 모두 극복 시:
- AR-cited 셀 35 → ~70 (143 셀 중 약 49%).
- Audit opinion AR-cited peer 1 (BKDP) → 7+ (DMIG·MDLN·PIPG·GOLF·KIJA·SMDM·KPIG).
- 6-peer Golf FY22 매출 시계열 100% AR-cited.
- 정정 (CORRECTIONS.md) 11건 (Cycle 87 self-correction 포함) → 추가 정정 잠재력 (curated 미검증 값 외부 source 검증 후).

본 페이지는 매 사이클 한계 극복 시 갱신.
