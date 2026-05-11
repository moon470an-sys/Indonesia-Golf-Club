# 운영 벤치마크 — 재검증 로그

> **메타 문서 cross-reference**: [README.md](README.md) · [IMPROVEMENT_LOG.md](IMPROVEMENT_LOG.md) · verification_log.md (본 문서) · [CORRECTIONS.md](CORRECTIONS.md) · [LIMITATIONS.md](LIMITATIONS.md) · [INVENTORY.md](INVENTORY.md)

페이지별 표·수치·서술의 AR 출처 정합성 검증. 사이클별 누적.

검증 항목
- (a) AR 출처(페이지/Note 번호) 명시되었는가?
- (b) raw AR PDF / curated CSV와 수치 일치하는가?
- (c) "공시 없음" 표기가 정확한가 (실제 공시 누락 없는가)?
- (d) 원칙 1~5 위반 서술이 남아 있는가?

---

## Cycle 1 — 2026-05-11

### index.html
- (a) ✓ 카테고리 카드 + 13개사 메타 표시. 절대 수치는 합계·중앙값만, 출처는 AR 공시분.
- (b) **수정**: "22,424bn 합계 매출"은 그룹 합산 peer + pure-play를 혼재 합산한 값. 골프 단독 매출은 DMIG 253 bn / PIPG 198 bn / GOLF Black Rocks 198 bn / MDLN segment 74 bn — 합계 약 723 bn. "그룹사 합산"은 별도 라벨. → 표기 변경 완료.
- (c) "FY2024 매출 공시 10/13"은 그룹 매출 기준. 골프 segment 분리 공시는 별도로 n/13 표기 추가.
- (d) 일반론적 introductory 문구 일부 다듬음. 운영 총괄 관점으로 lede 재작성.

### unit-economics.html (신규)
- (a) ✓ DMIG·PIPG·GOLF·MDLN segment 공시분만 게재. 각 셀에 AR 페이지·Note 번호 인라인.
- (b) DMIG 매출 FY24 = 253.10 bn (FY24 AR p.86 Note 23 Jumlah). PIPG FY24 = 197.57 bn (curated CSV; AR 직접 확인 Cycle 2).
- (c) 회원 수는 DMIG·PIPG만 일부 공시. 나머지는 "공시 없음".
- (d) ✓ Matoa 비교 없음. 일반 산업 평균 없음.

### revenue.html
- (a) ✓ DMIG 7 라인 매출 분해 FY22-24 (FY22/23 = AR p.89 Note 23; FY24 = AR p.86 Note 23).
- (b) **수정**: 기존 페이지의 DMIG FY23 매출 표기 "74.29 bn"은 실제 COGS Jumlah. 실 매출 245 bn으로 정정.
- (c) 세그먼트 분해 (Green Fee / 회원권 / F&B / 부속 / 부동산) 공시 매트릭스 표 추가. DMIG·PIPG는 분해 공시, 나머지는 단일 라인 또는 그룹 합산.
- (d) "운영 총괄이 X해야 한다"식 권고 서술 제거.

### cost-hr.html
- (a) ✓ DMIG 매출원가 3 라인 + 판관비 17 라인 모두 절대 금액 + YoY + 매출 비중 + Note 번호 명시.
- (b) ✓ FY24 AR p.86-87 Note 24/25 = Total COGS 77.05 bn / OpEx 97.13 bn 검증 일치.
- (c) 12개 비교 peer 컬럼은 "공시 없음 (Cycle N 추출 예정)" 명시.
- (d) 일반론적 "비용 절감 시사점" 제거.

### assets.html
- (a) 토지·홀·총자산은 기존 페이지 유지 + 부속 시설 매출 기여 섹션 신규.
- (b) DMIG The Range FY23 매출 Rp 31.35 bn은 FY23 AR p.18 BoD 보고 인용 (Note가 아닌 management discussion).
- (c) 드라이빙 레인지 베이 수·호텔 객실 수·볼룸 좌석 등은 13개사 중 일부만 AR 공시. n/13 표기.
- (d) ✓ Matoa 비교 없음.

### risk.html
- (a) ✓ 손실 peer (MDLN -690.3 bn FY24 / BKDP -35.9 bn FY24) AR 원인 직접 인용 유지.
- (b) 회원권 운영 이슈 (DMIG refundable membership Note 18 / SMDM 회원 노령화)는 AR 공시분 인용.
- (c) 일반론 체크리스트 제거 또는 "peer 공시 0건" 표기 완료.
- (d) "운영자가 주의해야 할 점" 등 prescriptive 문구 제거.

---

## Cycle 2 — 2026-05-11 — PIPG 추가 + DMIG vs PIPG 정합성 검증

### cost-hr.html
- (a) ✓ PIPG 3개 신규 표 모두 라인별 AR Note 번호·페이지 명시 (Note 27 p.141 / Note 28 p.142 / Note 29 p.142).
- (b) PIPG FY24 매출 197,571 m 검증: AR p.11 Ikhtisar = 197,570,521 ribu + p.91 Income Statement = 197,570,521,436 + p.141 Note 27 Jumlah = 197,570,521,436 — 3 출처 모두 일치 ✓. COGS 69,577 m 검증 동일. OpEx 76,117 m 검증 동일.
- (c) "동일 양식 12개 비교 peer" 매트릭스에서 PIPG·DMIG 컬럼 정량 채움 완료 (9 라인). 나머지 11개 peer는 Cycle 3+.
- (d) 일반론 없음. DMIG vs PIPG 사실 기록만.

### unit-economics.html
- (a) ✓ PIPG 단위 경제 표 모든 행에 출처 인라인 (p.7 Profil + p.11 Ikhtisar + p.141 Note 27).
- (b) PIPG 홀당 매출 10,976 m = 197,571 / 18 (검증) ✓. ha당 매출 3,727 m = 197,571 / 53.01 (검증) ✓.
- (c) PIPG 정규직 수는 SDM section 추출 미완 (Cycle 3). PIPG 회원 수는 AR 정량 미공시.
- (d) DMIG vs PIPG 비교 note는 절대값 사실 + 인구통계 차이 (도시 입지 vs 교외) 정성 설명까지. 추정 없음.

### revenue.html
- (a) ✓ PIPG 11-라인 stacked bar의 각 비율은 절대 금액 (FY24 AR p.141)에서 직접 계산.
- (b) FY23 매출 203,092 / FY24 197,571 검증 일치 (Note 27 + Ikhtisar + Income Statement).
- (c) PIPG Indonesia Open 토너먼트 매출(FY23 20,270 m)·원가(FY23 18,336 m)는 AR Note 27/28에 별도 라인으로 표기되어 FY24 부재 시 비교 가능.
- (d) "운영자가 …해야 한다" 식 prescriptive 표현 없음.

### risk.html
- (a) ✓ PIPG HGB 만료 2025·2055년 = FY24 AR p.131 Note 10 직접 인용. PIPG Note 32 임차/임대 약정 = AR p.143 직접 인용.
- (b) HGB 209,533 m² + Hak Pakai 40,319 m² (FY24 deferred charges) 모두 검증 ✓. 임차료 단가 (Rp 786,597,278 / Rp 825,927,141 / Rp 867,223,498) AR 원문 일치.
- (c) DMIG 토지권 만료년은 여전히 미추출 (Cycle 3). 11개 peer 미공시 표기 적정.
- (d) "BPN 직접 조회 필수" 등 인수자 권고 문구 제거됨 (Cycle 1에서 이미). PIPG 사례 추가는 사실 인용만.

### index.html
- 변경 없음 (Cycle 2에서 PIPG 사례를 반영하기에는 너무 상세 — Cycle 3에서 헤드 카운트 갱신 검토).

---

## Cycle 3 — 2026-05-11 — DMIG 손익 검증 + GOLF AR 직접 추출

### cost-hr.html
- (a) ✓ GOLF 4 segment 매출/COGS + Selling 5 + G&A 16 모두 라인별 AR 출처 (Note 29-32, p.210-212) 인라인.
- (b) GOLF FY24 매출 197,994 m 검증: AR p.10 Ikhtisar + p.160 Income Statement + p.210 Note 29 a Jumlah 3 출처 일치 ✓. COGS 78,273 m 검증 동일.
- (c) "동일 양식 12개 비교 peer" 매트릭스 GOLF 컬럼 9 라인 + 신규 2 라인 (Iklan/Keamanan) 채움. 나머지 10 peer는 Cycle 4+.
- (d) "GOLF의 Golf segment GP가 13개 peer 중 가장 높음" 객관적 사실 + 비교 note에 추정·일반론 없음.

### risk.html
- (a) ✓ GOLF PT Triniti Garam Properti 34% (FY24) / 25% (FY23) 매출 집중 = FY24 AR p.211 Note 29 (continued) 직접 인용. DMIG 명시적 부정 ("Tidak terdapat pendapatan Perusahaan yang melebihi 10%") = FY24 AR p.86 Note 23 직접 인용.
- (b) GOLF 67,856 m / 197,994 m = 34.27% ≈ 34% (AR 표기 일치) ✓.
- (c) Cycle 3 신규 섹션 "매출 집중 위험" 추가 — peer 공시 사례만, 일반론 체크리스트 없음.
- (d) prescriptive 표현 없음. AR 공시 텍스트만.

### unit-economics.html
- (a) ✓ GOLF tile + 표 모든 행에 출처 인라인 (p.10, p.62, p.210).
- (b) GOLF Golf 홀당 매출 2,585 m = 93,042 / 36 (연결 NKG+SGU) ✓. ha당 543 m = 93,042 / 171.2 ✓.
- (c) BGR Belitung은 entitas asosiasi (비연결)이므로 연결 영업 지표는 NKG+SGU만 사용. 54 hole / 243.4 ha는 참고 표기로 별도 행 분리.
- (d) DMIG vs PIPG vs GOLF 비교 note에 사실 + 입지 차이 정성 설명까지. "PIPG가 X해야 한다" 식 prescriptive 표현 없음.

### revenue.html
- (a) ✓ GOLF row "Golf 93,042 + Restoran 27,211 (FY24 AR p.210 Note 29 a)" 출처 명시.
- (b) GOLF segment 매출 93.042 + 67.856 + 27.211 + 9.885 = 197.994 (Jumlah) 일치 ✓.
- (c) MDLN/KIJA/SMDM/KPIG 행은 Cycle 1에서 curated 그대로 유지. Cycle 4에서 AR 직접 검증.

### Cycle 3 종료 점검
- (a) AR 출처 명시 비율: 핵심 5 페이지에서 95% 이상 (DMIG·PIPG·GOLF 데이터 인라인 추가).
- (b) raw AR 일치: 직접 검증 peer (DMIG/PIPG/GOLF) 모두 다중 출처 cross-check 완료. 차이 0건.
- (c) "공시 없음" 표기: GOLF에서 "F&B GP만 별도 매출원가 세분화 미공시" 정확. PIPG에서 캐디 인원 공시 없음, 명시.
- (d) 원칙 위반: cost-hr.html "DMIG vs PIPG vs GOLF 직접 비교" note는 사실 + 입지/회원제/segment-만에 비롯된 차이의 객관적 기술. "운영자가 …해야" 표현 없음.

---

## Cycle 34 — 2026-05-11 — Cross-page 일관성 audit

### 전수 검증 결과
- **DMIG FY24 매출**: 5 페이지 + overview.html + JSON 모두 Rp 253,102 m / 253.10 bn / 253.1 bn 일관 (소수점 표기만 다름). ✓
- **DMIG 정규직 198명**: unit-economics / assets / overview / TLDR 일치. ✓
- **PIPG GP 마진 표기 nuance 발견**:
  - **Golf course line GP 마진 = 63.4%** (Note 27 Golf course 53.87 vs Note 28 Golf course COGS 19.73) — Cycle 6/13/19/20/24/26 표기에 사용.
  - **전체 P&L GP 마진 = 64.8%** (총매출 197.57 vs 총 COGS 69.58) — Cycle 7 GP YoY 표에 사용 (cost-hr.html).
  - 두 값 모두 AR 직접 산출 정확. 둘은 다른 metric (segment line vs full P&L). 본 사이트는 6-peer Golf 비교에는 63.4% 사용, 전체 마진 비교에는 64.8% 사용.
- **6-peer Golf GP 마진 horizontal bar** (cost-hr.html Cycle 6): 65.7/63.4/58.6/44.5/41.6/38.9 = 모든 페이지 일치 ✓.
- **SMDM Golf 매출 시계열**: FY22 51.663 / FY23 58.197 / FY24 63.282 bn = 5 페이지 + JSON 일관 ✓.
- **GOLF 매출 집중 34%**: revenue.html / risk.html / overview.html 모두 동일 ✓.

### Cycle 34 의의
- 본 사이트의 핵심 수치 (peer별 매출·GP·인력·시설) 모두 5 페이지 + overview + JSON 일관성 확보.
- PIPG GP 마진 nuance 명시 → 사용자가 metric 차이를 이해.

### 후속 권고 (Cycle 35+)
- PIPG GP 마진 metric을 cost-hr.html Cycle 7 GP YoY 표에 "(전체 P&L)" 명시 추가 (Cycle 35).
- 6-peer 핵심 ratio summary 표에 "Golf line GP" vs "전체 P&L GP" 컬럼 분리 검토.

---

## Cycle 43 — 2026-05-11 — HTML 구조 integrity audit

### 검증 결과
- 7 페이지 (index·overview·unit-economics·revenue·cost-hr·assets·risk) section/body/table 태그 모두 balanced.
- **revenue.html div 불일치 1건 발견 + 수정**: Cycle 17에서 추가한 7-peer 미공시 메타 box의 외부 `<div class="note">`가 닫히지 않음. line 190 `</div>` 추가하여 349/349 균형 복원.
- 다른 6 페이지 div 균형 완벽.

### Cycle 43 의의
- 본 사이트의 42 cycle 누적 HTML 편집에서 발생한 유일한 구조 오류 (revenue.html div 1개 누락) 발견 + 즉시 수정.
- 모든 페이지 HTML 구조 정합성 확인 → 브라우저 렌더링 안정성 보장.

---

## Cycle 44-82 검증 summary

### 데이터 검증 (cross-cycle)
- Cycle 62-71: FY25 AR 가용 4 peer (GOLF·MDLN·KIJA·SMDM) + KPIG. 모든 추출 다중 출처 cross-check.
- Cycle 65: KIJA FY24 데이터 (Cycle 5 추출) FY25 AR comparative column으로 100% verified.
- Cycle 67: SMDM FY25 AR p.300 "restatement" 표 발견 — Cycle 64 발견 caveat 추가.
- Cycle 77-81: 5 peer JSON FY25 follow-up 데이터 영속화 + peers_summary regenerate.

### HTML 구조 (Cycle 43 audit 후 stable)
- Cycle 44-82 누적 편집에서 새 구조 오류 0건.
- 7 페이지 div/section/table tag 모두 balanced 유지.

### 메타 일관성 (Cycle 51 cache-bust 통일 후)
- ops-style.css v51 (Cycle 51) 후 새 cache-bust 추가 없음 (필요 없음).
- 6 메타 문서 모두 Cycle 46에 cross-reference link map 추가됨.

---

## Cycle 138-142 검증 summary (Cycle 142)

### Sequence integrity audit (Cycle 138)
- IMPROVEMENT_LOG.md entries 1-138 vs `seq 1 138`: Cycle 26 missing 발견 → 사후 보강 (Cycle 138).
- 138 cycle 동안 sequence gap을 한 번도 검증하지 않은 점이 본 발견의 의미. 향후 cycle 50 또는 100마다 정기 sequence audit 권장.

### Cycle 140 종합 audit (5 dimensions)
- HTML 7/7 balanced ✓
- Stale placeholder 1건 잔존 → Cycle 140에서 정리 → **절대 0건 달성** (regex 어떤 패턴도 매칭 없음).
- IMPROVEMENT_LOG entry 139/139 complete (Cycle 138 보강 후).
- Data 15 JSON 149.0 KB.
- Big counter 일관 (index.html bignum-row 139).

### History table & 통계 동기화 (Cycle 139)
- History table에 Cycle 125-138 14행 + Cycle 141 추가 = 누적 row coverage 100%.
- 누적 통계 블록 Cycle 138 종료 시점 갱신 + 2 신규 라인 (placeholder 0건 + entry 138 완전).

### Cycle 141 cost-hr.html 검증
- "Cycle N" 참조 10개 매칭 모두 historical fact 확인.
- placeholder 0건 재확인.

### Cycle 142 검증 결과
- 본 사이트 142 cycle 누적 변경 사항 100% 추적 가능 (history table + 상세 entry + 모든 페이지 footer cycle 정확).
- Stale placeholder 절대 0건 유지.
- 모든 정량 데이터 출처 인라인 (AR 페이지/Note 또는 메타 cycle 인용).

---

## Cycle 132-137 검증 summary (Cycle 137)

### Stale placeholder 정리 (Cycle 132-136)
- Cycle 132: cost-hr.html 기타 7개사 "Cycle 28+ 검토" 2건 → Cycle 92-103 검증 결과로 정리.
- Cycle 133: risk.html 5개 "Cycle 28+ 추출" placeholder + 1 "Cycle 5+ 추출" → 사실 명시.
- Cycle 134: index.html 매트릭스 5개 "Cycle 17+" (감사의견 5 peer) → "미추출".
- Cycle 135: risk.html 2개 "Cycle 4+/28+" + footnote "Cycle 27 종료 시점" → "본 사이트 미추출" + BSDE FY25 Note 58 추가.
- Cycle 136: risk.html "Cycle 3+/28+" + revenue.html "Cycle 14+" → 사실 명시 + cross-link.

### Cycle 137 최종 audit 결과
- HTML 7/7 페이지 div/section 모두 balanced ✓.
- stale "Cycle N+ 추출" placeholder: **0건** (단 1건 남은 "Cycle 14+" 표현은 "Cycle 14에서 시작" 의미로 positive context, 한계 placeholder 아님).
- 사이트 100+ cycle 누적 placeholder 부채 모두 해소.

### 누적 검증 (Cycle 137 시점)
- 13/13 peer AR 직접 추출 검증 완료.
- 137 cycle 누적 HTML integrity audit 5회 + 페이지별 footer cycle 정확성 100%.
- 메타 11건 정정 카운트 6 메타 파일 + 모든 HTML 일관.

---

## Cycle 114-125 검증 summary (Cycle 126)

### 메타 일관성 audit (Cycle 115·116·118·122)
- Cycle 115: 5 HTML 페이지 "10건/9건/7건" → "11건" 일괄 갱신 (overview·index 3곳·revenue·cost-hr).
- Cycle 116: 추가 stale 정정 (index.html line 474·revenue.html line 960) 11건으로 정리.
- Cycle 118: 사이트 종합 audit (HTML 7/7 OK / data 15 JSON 149.0 KB / 메타 11건 표기 모두 일치).
- Cycle 122: footer cycle 일관성 audit (7 HTML 페이지 footer 내부 최대 cycle과 100% 일치).

### 컨텐츠 갱신 (Cycle 114·120·121·123·124)
- Cycle 114: overview FY25 박스 7 peer + 13/13 완주 명시.
- Cycle 120·121: risk·overview footer Cycle 정확화.
- Cycle 123·124: README + overview "핵심 발견 5 → 7" 신규 #6·#7 (FY25 era + 13/13 완주) 추가.

### History table 추적 완전 (Cycle 117·119·125)
- Cycle 117: history 106-116 + 통계 6/7.
- Cycle 119: history 117-118 + audit 통합.
- Cycle 125: history 119-124 + Cycle 124 종료 통계.

### 원칙 위반 점검 (Cycle 114-125 누적)
- 추가 fabrication 사례 0건.
- 추가 추정·해석 표현 발생 0건.
- 모든 메타·HTML 페이지 변경이 사실 기반 + 출처 명시.

---

## Cycle 109-113 검증 summary (Cycle 113)

### HTML 구조 (post-Cycle-108)
- Cycle 110 assets.html "4. FY25 시설 후속" 신설: section 5 → 6, div 60 → 63.
- Cycle 112 unit-economics.html "FY25 단위 경제 후속" 신설: section 7 → 8, div 142 → 145.
- Cycle 113 audit: 7 페이지 전수 모두 div/section balanced. 신규 추가 후에도 무결성 유지.

### FY25 follow-up 페이지 노출 변화
- Cycle 73 (risk.html) → Cycle 84 (revenue.html) → Cycle 85 (overview.html) → Cycle 86 (cost-hr.html) → Cycle 110 (assets.html) → Cycle 112 (unit-economics.html).
- **6/7 페이지 FY25 노출 완료** (잔여: index.html은 13-peer 매트릭스에 "13/13 완주" 강조 박스로 대체).

### 데이터 검증
- 모든 신규 FY25 섹션은 출처 페이지/Note + 관련 cycle 인라인 명시.
- assets.html FY25 후속: 자산 증가 (MDLN Penyusutan +104.1%) 해석을 "AR Note 11 별도 검증 필요" caveat로 처리.
- unit-economics.html FY25 후속: 분자·분모 둘 다 누락된 점을 투명 표기.

---

## Cycle 91-108 검증 summary (Cycle 109)

### 데이터 검증 (post-Cycle-90 expansion)
- Cycle 92: BKDP FY25 P&L AR att2 p.70 직접 추출 — 모든 수치 inline 인용 가능.
- Cycle 95: SMRA FY25 Note 31·32 직접 추출 — Rekreasi/Leisure 통합 라인 명확히 표기.
- Cycle 98: **BSDE FY25 segment 추출 성공 (Cycle 56 실패 해소)** — FY24 image-PDF 추정에서 FY25 텍스트 가용으로 해소.
- Cycle 101·102·103: DILD·MKPI·BKSL FY25 segment 추출 — 모두 Golf segment 없음 직접 확인.
- **13/13 peer 추출 완주** (Cycle 103). peers_summary.json Cycle 105 13 peer 79.0 KB regenerate.

### HTML 구조 (Cycle 90/98/108 audit)
- Cycle 90·98·108 audit 3회 모두 7 페이지 div/section/table balanced.
- risk.html div 69 (Cycle 90) → 75 (Cycle 98, +6 = 2 new kv) → 75 (Cycle 108).
- index.html div 44 (Cycle 90) → 44 (Cycle 98) → 46 (Cycle 108, +2 = Cycle 107 note box).
- 누적 50+ cycle 연속 무결성 유지 (Cycle 43 정정 후).

### 메타 일관성 (Cycle 88·97·105·106 갱신)
- 정정 카운트 11건 (Cycle 87): 5 메타 파일 7 위치 동기화 (Cycle 88).
- peers_summary regenerate 3회 (Cycle 33·81·97·105 = 4번): 55.7 KB → 63.8 KB → 67.3 KB → 79.0 KB.
- IMPROVEMENT_LOG history table: Cycle 1-105 모두 채워짐 (Cycle 106).
- README.md 데이터 JSON 섹션 Cycle 108 13/13 완주 + 6 신규 명시.
- overview.html FY25 7 peer 카운트 (Cycle 96).

### 원칙 위반 점검 (Cycle 86·93)
- Cycle 86 작성 중 fabrication self-detect + 정정 (CORRECTIONS #11).
- Cycle 93 "FY24 Going Concern uncertainty 유지 추정" → "Cycle 12 텍스트 검증"으로 수정 (추정 → 사실).

### 신규 발견 사항 (Cycle 92-103)
- BKDP FY25: 매출 +20.0% 회복 but Gross Loss 지속 -5.73 bn (FY24 -8.12 bn → 29.4% 손실 축소).
- SMRA FY25: Leisure GP 마진 18.0% → 10.8% (-7.2pp), 매출 -8.3%, COGS -0.3% — operating leverage 악화.
- BSDE FY25: Consolidated 매출 -7.3%, Hotel +193.7%, Jalan tol -85.0% (대규모 segment shift).
- DILD FY25: Land segment result +72.8% / High Rise -49.6%.
- MKPI FY25: Operating income Rp 1,240 bn / Net Rp 1,122 bn (안정).
- BKSL FY25: Real Estat segment 매출 Rp 2,490 bn / Net profit Rp 833 bn.
- **공통**: 6 peer 모두 Golf segment 분리 공시 없음 → 본 사이트 핵심 비교 대상 외 유지.

---

## Cycle 83-90 검증 summary (Cycle 91)

### 데이터 검증 (post-plateau)
- Cycle 84: revenue.html FY25 표 6행 — 모든 수치는 risk.html Cycle 73 + JSON 데이터와 cross-match 확인.
- Cycle 86: cost-hr.html MDLN FY25 표 4행 — **작성 중 fabrication 발견 + 동일 사이클 내 자기 정정** (mdln_notes.json 직접 대조). 자기 발견 정정의 첫 사례. CORRECTIONS #11 (Cycle 87) 정식 기록.
- Cycle 86 정정 후 모든 수치: Gaji 19,250 / Penyusutan 2,756 / Lain-lain 9,425 / 합계 31,431 m (FY24, mdln_notes.json line 79-83 직접 일치).

### HTML 구조 (Cycle 90 audit)
- 7 페이지 전수 audit: div/section/table 모두 0 errors.
- revenue.html section 10 → 11 (Cycle 84 추가), cost-hr.html section 14 → 15 (Cycle 86 추가).
- Cycle 43 div 정정 이후 47 cycle 연속 무결성 유지.

### 메타 일관성 (Cycle 88 갱신 후)
- 정정 카운트 5 메타 파일 7 위치 모두 11건으로 동기화 (Cycle 88).
- IMPROVEMENT_LOG history table Cycle 1-89 모두 채워짐 (Cycle 82·89).
- 누적 통계 블록 "Cycle 48 종료" → "Cycle 88 종료" 갱신 (Cycle 89).

### 원칙 위반 점검
- spec 원칙 (2) "추정·해석·일반론·Matoa 비교 금지" — Cycle 86 작성 중 "신규 자산 도입 가능성 시사" 표현 발견, 즉시 "자산 증가의 구체적 내용은 AR Note 11 별도 검증 필요 — 본 사이트 미추출"로 수정.

---

## Cycle 4 — 2026-05-11 — MDLN Note 25/26 + 매입 집중

### cost-hr.html
- (a) ✓ MDLN 매출/원가 라인별 출처 모두 명시 (Note 25 p.318 / Note 26 p.318-319).
- (b) MDLN Golf 56,640 + F&B 17,735 = 74,375 검증: Note 25 sub-total 일치 ✓. COGS Golf 31,432 + F&B 13,430 = 44,862 검증: Note 26 "Beban langsung" sub-total 일치 ✓.
- (c) "동일 양식 비교 peer" 매트릭스에서 MDLN Golf segment 직접 라인 (Gaji 19,250+5,893 / Penyusutan 2,756 / F&B materials 5,793) 채움. F&B 식자재 신규 행 추가.
- (d) "MDLN Golf 단독 GP 44.5% = 13개 peer 중 최저"는 4 peer 비교 사실 기록만.

### risk.html
- (a) ✓ MDLN PT Jumbo Power International 62 bn 매입 집중 = FY24 AR att2 p.319 Note 26 직접 인용.
- (b) Rp 62,020,000,000 / Total COGS 581 bn ≈ 10.7% (AR "melebihi 10%" 일치) ✓.
- (c) FY23 미발생 명시 ("Pada tahun 2023, tidak ada beban pokok yang melebihi 10%") = AR 직접 인용.
- (d) 매출 집중 + 매입 집중 = AR의 "사실 공시 사례"만, 일반론 권고 없음.

### unit-economics.html
- (a) ✓ MDLN row 출처 (Note 25 p.318) 명시. 분석 대상 표 + 비교 표 MDLN 행 정량.
- (b) MDLN Pure golf 56,640 + F&B 17,735 = 74,375 sub 분해 합산 검증 ✓.
- (c) MDLN 홀 수·코스 면적 AR 정량 미공시 → "미공시" 명시 (curated에서도 미수집).
- (d) MDLN row에서 Golf 단독 unit-economics 비교 불가 (홀·면적 미공시). prescriptive 표현 없음.

### Cycle 4 종료 검증
- MDLN 라인 수: 매출 11 (그룹) / 매출 4 (golf+F&B) + COGS Golf 3 + COGS F&B 3 = 본 사이트 cost-hr.html 표에 모두 분해 표기.
- 4 peer (DMIG·PIPG·GOLF·MDLN) 모두 Golf 단독 매출 + Golf 단독 COGS 분리 공시 → Golf GP 마진 직접 비교 가능 (58.6% / 63.4% / 65.7% / 44.5%). 나머지 9 peer는 Golf 단독 분리 없음.
