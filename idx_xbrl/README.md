# IDX XBRL 자동 갱신

site의 재무 데이터(`data/company_financials_5y.json`)를 IDX (Indonesia Stock Exchange)의 XBRL 인스턴스에서 직접 추출하여 주기적으로 갱신.

## 파일

- `parse_xbrl.py` — IDX XBRL 인스턴스(zip 또는 .xbrl)에서 표준 재무 필드 추출 (lxml)
- `download_idx.py` — IDX e-laporan API에서 ticker별 instance.zip 다운로드 (cloudscraper로 Cloudflare 우회)
- `update_financials.py` — 다운로드 + 파싱 + JSON 머지 + 로그/백업 일괄 처리
- `run_weekly.ps1` — Task Scheduler에서 호출되는 진입점 (update + git commit/push)
- `register_task.ps1` — Task Scheduler 등록·해제·즉시실행
- `cache/` — 다운로드한 XBRL zip (재실행 시 캐시 적중하면 다운로드 생략)
- `logs/` — 매 실행마다 JSON 로그 (`xbrl_update_YYYYMMDD_HHMMSS.json`) + PowerShell 로그 (`run_weekly_*.log`)

## 의존성

```powershell
python -m pip install cloudscraper lxml requests
```

## 수동 실행

```powershell
# 단일 ticker 실험
python -X utf8 update_financials.py --year 2024 --tickers BSDE --dry-run

# 24개 ticker 전체 (cache 활용)
python -X utf8 update_financials.py --year 2024

# cache 무시하고 재다운로드
python -X utf8 update_financials.py --year 2024 --no-cache
```

## Task Scheduler 등록 (매주 일요일 02:00)

```powershell
cd "C:\Users\yoonseok.moon\OneDrive - (주) ST International\Projects\Matoa 골프장\site\idx_xbrl"
.\register_task.ps1                # 등록
.\register_task.ps1 -RunNow        # 즉시 한 번 실행 (테스트)
.\register_task.ps1 -Unregister    # 해제
```

작업명: `MatoaGolfIDXXBRLWeekly`. 등록 후 `taskschd.msc`에서 확인 가능.

## 동작

1. `data/golf_courses.json`에서 unique IDX 티커(24개) 수집
2. 각 티커마다 IDX e-laporan API 호출 → `instance.zip` 다운로드 (캐시)
3. lxml로 `idx-cor:*` 태그 파싱 (revenue, net_profit, total_assets/liabilities/equity, EPS, cash flow 등)
4. `company_financials_5y.json`의 `companies[].yearly[YEAR]`에 머지:
   - 숫자 필드는 XBRL 정확값으로 덮어쓰기
   - `sources` 배열 맨 앞에 `source_type: "IDX_XBRL"` 출처 삽입
   - `data_quality_year: "xbrl_audited"` 마킹
   - 신규 ticker는 새 company entry 자동 생성
5. 원본 백업(`*.backup.xbrl.YYYYMMDD_HHMMSS.json`) → 저장
6. (Task Scheduler 모드) git add/commit/push origin main

## 비상장 ticker

DMIG (Damai Indah Golf)와 PIPG (Pondok Indah Golf)는 IDX 비상장 — `not_found`로 처리되며 기존 JSON 데이터는 보존.
