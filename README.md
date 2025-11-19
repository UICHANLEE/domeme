# 도매꾹 웹 스크래핑 프로젝트

도매꾹(domemedb.domeggook.com) 사이트에 접속하고 데이터를 수집하는 프로젝트입니다.

## 프로젝트 구조

```
domeme/
├── main.py          # 메인 실행 파일 (CLI 인터페이스)
├── app.py           # Streamlit GUI 인터페이스 ⭐ NEW!
├── config.py        # 설정 관리
├── logger.py        # 로깅 설정
├── scraper.py       # 웹 드라이버 및 기본 접속
├── login.py         # 로그인 기능
├── search.py        # 상품 검색 기능
├── parser.py        # 검색 결과 파싱
├── mybox.py         # 마이박스 관련 기능
├── utils.py         # 유틸리티 함수
├── requirements.txt  # 의존성 패키지
└── result/          # 검색 결과 저장 폴더
```

## 설치 방법

1. Python 가상환경 생성 (권장):
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
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

### 🖥️ GUI 사용 (권장) ⭐ NEW!

**Streamlit 기반 웹 GUI를 사용하면 모든 옵션을 쉽게 선택할 수 있습니다!**

```bash
# GUI 실행
streamlit run app.py
```

실행하면 브라우저가 자동으로 열리며 웹 인터페이스가 표시됩니다.

**GUI 주요 기능:**
- ✅ 검색어 직접 입력 또는 파일 업로드
- ✅ 인기 키워드 자동 수집
- ✅ 여러 쇼핑몰 동시 검색 선택
- ✅ 검색 옵션 시각적 설정 (가격 필터, 페이지 수 등)
- ✅ 실시간 검색 진행 상황 표시
- ✅ 검색 결과 테이블 및 통계 표시
- ✅ JSON→CSV 변환, CSV 병합 등 유틸리티 도구

**GUI 사용 예시:**
1. 사이드바에서 검색어 입력 방식 선택 (직접 입력/파일 업로드/인기 키워드)
2. 검색할 쇼핑몰 선택 (도매꾹, 쿠팡, 네이버 등)
3. 검색 옵션 설정 (최대 결과 수, 가격 필터 등)
4. 로그인 정보 입력 (선택사항)
5. "검색 시작" 버튼 클릭

### 기본 사용 (CLI - 대화형 모드)

**기본적으로 대화형 모드로 동작합니다.** 프로그램을 실행하면 검색어를 입력하라는 프롬프트가 나타납니다.

```bash
# 기본 실행 (대화형 모드)
python main.py

# 실행 후 검색어 입력:
# 검색어: 양말
# 또는 여러 개: 양말, 장갑, 모자
```

### 빠른 검색 모드

명령줄에서 검색어를 직접 지정하려면 `--quick` 또는 `-q` 옵션을 사용하세요.

```bash
# 단일 검색어 빠른 검색
python main.py --quick 양말
# 또는 짧은 형식
python main.py -q 양말

# 여러 검색어 빠른 검색
python main.py -q 양말 장갑 모자
```

### 주요 옵션

#### 검색 옵션

```bash
# 옵션만 지정하고 검색어는 대화형으로 입력받기
python main.py --max-results 10 --min-price 15000

# 빠른 검색 + 옵션 조합
python main.py -q 양말 --max-results 10 --min-price 15000

# 최소 가격 필터 (기본값: 12,000원)
python main.py --min-price 15000

# 가격 필터링 비활성화
python main.py --no-price-filter

# 여러 페이지 검색 (페이지네이션)
python main.py --pages 3  # 최대 3페이지까지 검색
```

#### 실행 옵션

```bash
# 헤드리스 모드 (브라우저 창 숨김)
python main.py --headless

# 마이박스에 추가하지 않고 검색만 수행
python main.py --no-mybox

# 검색 폼 사용 방식 (기본값: 직접 URL 접근)
python main.py --use-form
```

#### 출력 옵션

```bash
# 상세 출력
python main.py --verbose

# CSV 형식으로 저장
python main.py --format csv

# 결과를 파일로 저장하지 않음
python main.py --no-save

# result 폴더의 모든 JSON 파일을 CSV로 변환
python main.py --convert-json-to-csv

# CSV 변환 시 기존 파일 덮어쓰기
python main.py --convert-json-to-csv --overwrite-csv

# result 폴더의 모든 CSV 파일을 하나로 병합
python main.py --merge-csv

# 통합 CSV 파일의 출력 경로 지정 (프로젝트 루트에 저장)
python main.py --merge-csv --merge-output all_products.csv

# 검색어 컬럼 없이 병합
python main.py --merge-csv --no-keyword-column
```

#### 파일에서 검색어 읽기

검색어 목록이 있는 파일을 만들고:

```bash
# keywords.txt 파일 예시
양말
장갑
모자
```

```bash
python main.py --file keywords.txt
```

#### 인기 키워드 자동 수집 모드 ⭐ NEW!

외부 사이트에서 인기 키워드를 자동으로 수집하여 검색합니다.

```bash
# 기본 사용 (자동 모드, 50개 키워드) ⭐ 기본값 증가!
python main.py --trending

# 여러 소스를 동시에 활용하여 대량 키워드 수집 ⭐ NEW!
python main.py --trending --multi-source --trending-count 100

# 네이버 쇼핑에서 키워드 수집 (50개)
python main.py --trending --trending-source naver --trending-count 50

# 쿠팡에서 키워드 수집 (100개)
python main.py --trending --trending-source coupang --trending-count 100

# 아이템 스카우트에서 키워드 수집 (50개)
python main.py --trending --trending-source itemscout --trending-count 50

# 과거 검색 결과에서 키워드 추출
python main.py --trending --trending-source results --trending-count 50

# 인기 키워드 + 여러 페이지 검색
python main.py --trending --trending-count 20 --pages 3

# 인기 키워드 + 가격 필터
python main.py --trending --trending-source naver --min-price 15000

# 여러 소스 + 브랜드 제외 + 경쟁 분석 (일반 키워드만 발굴) ⭐ NEW!
python main.py --trending --multi-source --exclude-brands --analyze-competition --trending-count 100

# 아이템 스카우트에서 브랜드 제외 키워드만 수집
python main.py --trending --trending-source itemscout --exclude-brands --trending-count 50
```

**인기 키워드 소스 옵션:**
- `auto`: 자동으로 여러 소스 시도 (기본값)
- `naver`: 네이버 쇼핑 베스트 페이지
- `coupang`: 쿠팡 베스트셀러 페이지
- `itemscout`: 아이템 스카우트 트렌드 페이지
- `gmarket`: 지마켓 베스트 상품
- `11st`: 11번가 베스트셀러
- `google`: 구글 트렌드
- `products`: 도매꾹 인기 상품 목록
- `results`: 과거 검색 결과 파일 분석

**여러 소스 동시 활용 (`--multi-source`):**
- **8개 사이트에서 동시 수집**: 네이버 쇼핑, 네이버 데이터랩, 쿠팡, 쿠팡 트렌드, 아이템스카우트, 지마켓, 11번가, 구글 트렌드
- 중복 제거 및 품질 필터링 자동 수행
- 더 많은 키워드를 효율적으로 수집 가능
- 기본값: 50개 (기존 10개에서 증가)
- 각 소스에서 최소 15개씩 수집하여 최대 200개 이상의 키워드 수집 가능

#### 로그인 옵션

로그인 정보는 다음 우선순위로 사용됩니다:
1. 명령줄 옵션 (`--username`, `--password`)
2. 환경변수 (`DOMEID`, `DOMPWD`) ⭐ **권장**
3. 사용자 입력 요청

**방법 1: 명령줄에서 지정** (보안상 권장하지 않음)
```bash
python main.py --username your_id --password your_password
```

**방법 2: 환경변수 사용** ⭐ **권장**

**Windows PowerShell:**
```powershell
# 현재 세션에만 적용
$env:DOMEID="your_id"
$env:DOMPWD="your_password"

# 영구적으로 설정 (시스템 환경변수)
[Environment]::SetEnvironmentVariable("DOMEID", "your_id", "User")
[Environment]::SetEnvironmentVariable("DOMPWD", "your_password", "User")
```

**Windows CMD:**
```cmd
# 현재 세션에만 적용
set DOMEID=your_id
set DOMPWD=your_password

# 영구적으로 설정 (사용자 환경변수)
setx DOMEID "your_id"
setx DOMPWD "your_password"
```

**Linux/Mac:**
```bash
# 현재 세션에만 적용
export DOMEID="your_id"
export DOMPWD="your_password"

# 영구적으로 설정 (~/.bashrc 또는 ~/.zshrc에 추가)
echo 'export DOMEID="your_id"' >> ~/.bashrc
echo 'export DOMPWD="your_password"' >> ~/.bashrc
source ~/.bashrc
```

**방법 3: 사용자 입력** (환경변수가 없으면 자동으로 요청)
```bash
python main.py
# 실행 후 아이디와 비밀번호 입력 요청
```

> ⚠️ **보안 주의**: 명령줄에서 비밀번호를 직접 입력하면 명령어 히스토리에 남을 수 있으므로 환경변수 사용을 권장합니다.

#### 로깅 옵션

```bash
# 로그 레벨 설정
python main.py --log-level DEBUG

# 로그 파일 저장
python main.py --log-file logs/app.log
```

#### 쿠팡 쇼핑몰 및 네이버 쇼핑 검색 ⭐ NEW!

**쿠팡 쇼핑몰에서 검색:**

⚠️ **주의**: 쿠팡은 봇 차단이 매우 강력하여 접근이 제한될 수 있습니다. 네이버 쇼핑 사용을 권장합니다.

```bash
# 쿠팡 쇼핑몰에서 상품 검색 (접근 제한 가능)
python main.py -q 양말 --search-coupang

# 쿠팡에서 검색 + 가격 필터
python main.py -q 양말 --search-coupang --min-price 10000 --max-price 50000
```

**네이버 쇼핑에서 검색:**

```bash
# 네이버 쇼핑에서 상품 검색
python main.py -q 양말 --search-naver

# 네이버 쇼핑에서 검색 + 가격 필터
python main.py -q 양말 --search-naver --min-price 15000
```

**모든 사이트에서 동시 검색:**

```bash
# 도매꾹, 쿠팡, 네이버 쇼핑 모두에서 검색
python main.py -q 양말 --search-all

# 여러 키워드 + 모든 사이트 검색
python main.py -q 양말 장갑 모자 --search-all --max-results 30
```

**Python 스크립트에서 직접 사용:**

```python
# 쿠팡 쇼핑몰 검색
from coupang_shopping import search_coupang_products
from scraper import get_chrome_driver

driver = get_chrome_driver(headless=False)
products = search_coupang_products(driver, keyword="양말", max_results=50)
print(f"쿠팡에서 {len(products)}개 상품 발견")

# 네이버 쇼핑 검색
from naver_shopping import search_naver_shopping_products

products = search_naver_shopping_products(driver, keyword="양말", max_results=50)
print(f"네이버 쇼핑에서 {len(products)}개 상품 발견")
```

### 전체 옵션 보기

```bash
python main.py --help
```

## 기능

### 1. 상품 검색

- **직접 URL 접근 방식** (기본값): 검색어를 URL에 포함하여 직접 접근 (더 빠르고 안정적)
- **검색 폼 사용 방식**: 검색창에 키워드 입력 후 검색 버튼 클릭 (`--use-form` 옵션)
- **가격 필터링**: 지정한 가격 이상인 상품만 필터링 (기본값: 12,000원)
- 검색 결과 페이지에서 상품 정보 추출
- URL 변경 감지 및 검색 결과 로딩 대기
- 상품명, 가격, 링크, 이미지 등 정보 수집

### 2. 마이박스 기능

- 검색 결과에서 상품 선택
- 마이박스에 상품 추가
- 스피드고 전송 자동화

### 3. 결과 저장

- JSON 형식 (기본값)
- CSV 형식 (`--format csv` 옵션)
- `result/` 폴더에 자동 저장
- **JSON → CSV 일괄 변환**: `--convert-json-to-csv` 옵션으로 모든 JSON 파일을 한번에 CSV로 변환
- **CSV 파일 통합**: `--merge-csv` 옵션으로 모든 CSV 파일을 하나의 통합 파일로 병합 (검색어 컬럼 자동 추가)

### 4. 쿠팡 쇼핑몰 및 네이버 쇼핑 검색 ⭐ NEW!

- **쿠팡 쇼핑몰 검색**: www.coupang.com에서 상품 검색 및 정보 수집
- **네이버 쇼핑 검색**: shopping.naver.com에서 상품 검색 및 정보 수집
- **통합 검색**: 도매꾹, 쿠팡, 네이버 쇼핑에서 동시에 검색하여 결과 통합
- 각 상품에 소스 정보 자동 추가 (source 컬럼)

## 검색 결과 형식

검색 결과는 다음과 같은 정보를 포함합니다:

```json
{
  "name": "상품명",
  "product_id": "상품번호",
  "price": "29,530원",
  "price_value": 29530,
  "seller": "판매자명",
  "grade": "등급",
  "fast_delivery": true,
  "link": "https://domemedb.domeggook.com/index/item/itemView.php?itemNo=...",
  "image": "https://..."
}
```

## 사용 예시

### 예시 1: 기본 사용 (대화형 모드)

```bash
python main.py
# 실행 후 검색어 입력 프롬프트가 나타남
# 검색어: 양말
```

### 예시 2: 빠른 검색

```bash
# 단일 검색어
python main.py -q 양말

# 여러 검색어
python main.py -q 양말 장갑 모자
```

### 예시 3: 옵션과 함께 사용

```bash
# 옵션만 지정하고 검색어는 입력받기
python main.py --max-results 10 --min-price 15000

# 여러 페이지 검색
python main.py -q 양말 --pages 3

# 빠른 검색 + 옵션
python main.py -q 양말 --max-results 10 --min-price 15000

# 여러 페이지 + 최대 결과 수 제한
python main.py -q 양말 --pages 5 --max-results 100
```

### 예시 4: 파일에서 검색어 읽기

```bash
# keywords.txt 파일에 검색어 목록이 있는 경우
python main.py --file keywords.txt
```

### 예시 5: 검색만 수행 (마이박스 추가 안 함)

```bash
python main.py --no-mybox --format csv
# 또는 빠른 검색과 함께
python main.py -q 양말 --no-mybox --format csv
```

### 예시 6: 상세 출력

```bash
python main.py --verbose --log-level DEBUG
# 또는 빠른 검색과 함께
python main.py -q 양말 --verbose --log-level DEBUG
```

### 예시 7: 실전 사용 시나리오

```bash
# 시나리오 1: 대화형으로 여러 검색어 입력
python main.py
# 검색어: 양말, 장갑, 모자, 스카프

# 시나리오 2: 빠른 검색으로 즉시 실행
python main.py -q 양말 --headless --max-results 5

# 시나리오 3: 파일에서 읽어서 자동화
python main.py --file keywords.txt --headless --no-mybox --format csv
```

## 설정

### 환경변수

로그인 정보를 환경변수로 설정하면 매번 입력할 필요가 없습니다.

- `DOMEID`: 로그인 아이디
- `DOMPWD`: 로그인 비밀번호

**환경변수 설정 확인 방법:**

**Windows PowerShell:**
```powershell
# 환경변수 확인
echo $env:DOMEID
echo $env:DOMPWD
```

**Windows CMD:**
```cmd
# 환경변수 확인
echo %DOMEID%
echo %DOMPWD%
```

**Linux/Mac:**
```bash
# 환경변수 확인
echo $DOMEID
echo $DOMPWD
```

### config.py

주요 설정은 `config.py` 파일에서 관리됩니다:

- URL 설정
- CSS 선택자 설정
- 대기 시간 설정
- 기본값 설정

## 참고사항

- Selenium을 사용할 경우 ChromeDriver가 필요합니다.
- 기본적으로 헤드리스 모드가 아닙니다. 브라우저 창이 표시됩니다.
- 헤드리스 모드를 사용하려면 `--headless` 옵션을 사용하세요.
- 로그인 정보는 환경변수 사용을 권장합니다 (보안).

## 문제 해결

### ChromeDriver 오류

ChromeDriver가 설치되어 있지 않거나 버전이 맞지 않으면 오류가 발생할 수 있습니다.

```bash
# webdriver-manager 설치
pip install webdriver-manager

# 또는 ChromeDriver를 수동으로 설치
# https://chromedriver.chromium.org/downloads
```

### 로그인 실패

로그인 정보가 올바른지 확인하세요. 환경변수 또는 명령줄 옵션으로 지정할 수 있습니다.

### 검색 결과가 없음

- 검색어를 확인하세요
- 가격 필터를 조정해보세요 (`--no-price-filter` 옵션 사용)
- `--verbose` 옵션으로 상세 로그 확인

## 라이선스

이 프로젝트는 개인 사용 목적으로 제작되었습니다.
