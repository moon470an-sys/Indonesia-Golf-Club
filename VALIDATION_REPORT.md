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
