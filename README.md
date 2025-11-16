# 도매꾹 웹 스크래핑 프로젝트

도매꾹(domemedb.domeggook.com) 사이트에 접속하고 데이터를 수집하는 프로젝트입니다.

## 설치 방법

1. Python 가상환경 생성 (권장):
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

3. ChromeDriver 설치:
   - Selenium을 사용하려면 ChromeDriver가 필요합니다.
   - Chrome 브라우저 버전에 맞는 ChromeDriver를 다운로드하거나,
   - `pip install webdriver-manager`를 설치하여 자동으로 관리할 수 있습니다.

## 사용 방법

### 기본 사용 (대화형)

```bash
python main.py
```
실행 후 검색할 상품명을 입력하세요.

### 명령줄 인자로 검색어 지정

```bash
python main.py 양말
python main.py "겨울 장갑"
```

## 기능

- `access_with_requests()`: requests 라이브러리를 사용한 간단한 HTTP 요청
- `access_with_selenium()`: Selenium을 사용한 브라우저 자동화 접속
- `search_products(keyword, use_direct_url=False, min_price=None)`: 상품 검색 및 결과 수집
  - **직접 URL 접근 방식** (`use_direct_url=True`): 검색어를 URL에 포함하여 직접 접근 (기본값, 더 빠르고 안정적)
  - **검색 폼 사용 방식** (`use_direct_url=False`): 검색창에 키워드 입력 후 검색 버튼 클릭
  - **가격 필터링** (`min_price=12000`): 지정한 가격 이상인 상품만 필터링 (예: 12,000원 이상)
  - 검색 결과 페이지에서 상품 정보 추출
  - URL 변경 감지 및 검색 결과 로딩 대기
  - 상품명, 가격, 링크, 이미지 등 정보 수집
  - 결과를 JSON 파일로 저장

### 검색 방식

기본적으로 **직접 URL 접근 방식**을 사용합니다. 이 방식은:
- 검색어를 URL에 포함하여 `supplyList.php` 페이지로 직접 이동
- 검색 폼을 거치지 않아 더 빠르고 안정적
- URL 구조: `https://domemedb.domeggook.com/index/item/supplyList.php?sf=subject&enc=utf8&fromOversea=0&mode=search&sw={검색어}`

## 가격 필터링

기본적으로 **12,000원 이상**인 상품만 필터링합니다. 코드에서 `min_price` 파라미터를 변경하여 원하는 최소 가격을 설정할 수 있습니다:

```python
# 12,000원 이상인 상품만 검색
results = search_products("골프", min_price=12000)

# 50,000원 이상인 상품만 검색
results = search_products("골프", min_price=50000)

# 가격 필터링 없이 모든 상품 검색
results = search_products("골프", min_price=None)
```

## 검색 결과

검색 결과는 다음과 같은 정보를 포함합니다:
- `name`: 상품명
- `product_id`: 상품번호
- `price`: 가격 (천단위 콤마 포함, 예: "29,530원")
- `price_value`: 가격 숫자 값 (필터링용, 예: 29530)
- `seller`: 판매자 정보
- `grade`: 판매자 등급
- `fast_delivery`: 빠른배송 가능 여부 (True/False)
- `link`: 상품 상세 페이지 링크
- `image`: 상품 이미지 URL

결과는 `search_results_{검색어}.json` 파일로 자동 저장됩니다.

## 참고사항

- Selenium을 사용할 경우 ChromeDriver가 필요합니다.
- 헤드리스 모드로 실행되므로 브라우저 창이 표시되지 않습니다.
- 필요에 따라 헤드리스 모드를 해제할 수 있습니다 (`--headless` 옵션 제거).

