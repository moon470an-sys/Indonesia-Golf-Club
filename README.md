# Indonesia Golf Club Map

인도네시아 전역 **91개 골프장**의 위치와 정보를 인터랙티브 지도로 보여주는 GitHub Pages 사이트입니다.

🔗 **Live**: https://moon470an-sys.github.io/Indonesia-Golf-Club/

## 특징

- 📍 **91개 골프장** 마커 표시 (자카르타·발리·반둥·수라바야·빈탄·바탐 등 인도네시아 전역)
- 🔍 골프장 이름·지역·설계자 검색
- 🎯 지역별·홀 수별 필터
- 📋 마커/리스트 클릭 시 상세 정보 표시 (주소·홀 구성·설계자·부대시설·웹사이트)
- 📱 모바일 반응형
- 🆓 100% 무료 스택 (Leaflet + OpenStreetMap + Nominatim)

## 데이터

- 91개 골프장 정보를 `data/golf_courses.json`에 저장
- 좌표는 Nominatim (OpenStreetMap 무료 지오코딩)으로 확보
- 13곳은 도시 중심 좌표로 근사 표시 (`coord_approximate: true`)
- 출처: APLGI · GolfPass · GolfAsian · GolfLux · 공식 골프장 사이트

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
```

## License

데이터는 공개 출처 기반 정보의 큐레이션이며, 코드는 MIT 라이선스입니다.
