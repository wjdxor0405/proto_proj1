# 🚗 자동차 등록 & 기업 FAQ 대시보드

Streamlit 기반 데이터 조회 GUI 애플리케이션

---

## 주요 기능

### 1. 전국 자동차 등록 현황
- KOSIS 자동차등록대수현황 xlsx 자동 파싱
- 시도별 / 차종별 / 용도별 필터링
- 막대 차트, 파이 차트, 스택 차트
- 시군구 상세 조회
- **새 파일 추가 시 자동 인식** (확장 가능)

### 2. 기업 FAQ 조회
- Selenium + BeautifulSoup 기반 크롤링
- MySQL 누적 저장 및 조회
- 크롤링 세션별 결과 vs 전체 누적 데이터 구분
- **새 기업 추가 시 자동 확장** (DB에서 관리)

---

## 설치 및 실행

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. MySQL 설정 (FAQ 누적 저장 시 필요)
`utils/database.py`에서 DB_CONFIG 수정:
```python
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "your_password",  # 수정
    "database": "car_dashboard",
    ...
}
```

### 3. ChromeDriver 설치 (크롤링 시 필요)
```bash
# macOS
brew install chromedriver

# Ubuntu
sudo apt-get install chromium-chromedriver

# 또는 webdriver-manager 사용
pip install webdriver-manager
```

### 4. 앱 실행
```bash
cd car_dashboard
streamlit run app.py
```

---

## 프로젝트 구조

```
car_dashboard/
├── app.py                  # 메인 진입점
├── requirements.txt
├── data/                   # xlsx 파일 폴더 (자동 인식)
│   └── 자동차등록대수현황_시도별_*.xlsx
├── pages/
│   ├── car_page.py         # 자동차 등록 현황 페이지
│   └── faq_page.py         # FAQ 조회 페이지
├── utils/
│   ├── car_data.py         # xlsx 파싱 유틸
│   └── database.py         # MySQL 연동
└── crawlers/
    └── kia_crawler.py      # FAQ 크롤러 (범용 포함)
```

---

## 새 데이터 추가 방법

### 자동차 등록 현황 파일 추가
1. KOSIS에서 xlsx 다운로드
2. `data/` 폴더에 복사
3. 앱 새로고침 → 자동 인식

### 새 기업 FAQ 추가
1. 앱 실행 → [기업 FAQ 조회] → [기업 관리] 탭
2. 기업 코드 / 기업명 / FAQ URL 입력
3. DB에 저장 후 크롤링 실행

---

## MySQL 없이 사용
- 자동차 등록 현황: 정상 작동
- FAQ 크롤링: 가능 (단, DB 저장 불가)
- FAQ 누적 조회: 불가 (MySQL 필요)
- 임시 기업 추가: 세션 내에서만 유지

---

## 크롤러 확장
`crawlers/kia_crawler.py`의 `crawl_generic_faq()` 함수는
URL만 주면 범용으로 동작합니다.
특정 사이트 전용 크롤러가 필요하면 같은 패턴으로 추가하세요.
