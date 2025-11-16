# 도매꾹 웹 스크래핑 프로젝트

도매꾹(domemedb.domeggook.com) 사이트에 접속하고 데이터를 수집하는 프로젝트입니다.

## 프로젝트 구조

```
domeme/
├── main.py          # 메인 실행 파일 (CLI 인터페이스)
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

### 기본 사용 (대화형 모드)

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

# 빠른 검색 + 옵션
python main.py -q 양말 --max-results 10 --min-price 15000
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
