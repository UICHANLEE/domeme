# 30-40대 남성 구매 키워드 검색 가이드

## 생성된 키워드 파일
`keywords_30_40_male.txt` 파일에 30-40대 남성들이 주로 구매하는 상품 키워드가 포함되어 있습니다.

## 검색 실행 방법

### 1. 기본 검색 (도매꾹만)
```bash
python main.py --file keywords_30_40_male.txt --max-results 20
```

### 2. 모든 사이트에서 검색 (권장)
```bash
python main.py --file keywords_30_40_male.txt --search-all-sites --max-results 20 --format csv
```

### 3. 특정 사이트에서만 검색
```bash
# 쿠팡에서만
python main.py --file keywords_30_40_male.txt --search-coupang --max-results 20

# 네이버 쇼핑에서만
python main.py --file keywords_30_40_male.txt --search-naver --max-results 20

# 지마켓에서만
python main.py --file keywords_30_40_male.txt --search-gmarket --max-results 20
```

### 4. 가격 필터 적용
```bash
# 최소 가격 10,000원 이상
python main.py --file keywords_30_40_male.txt --search-all-sites --min-price 10000 --max-results 20

# 가격 범위 지정 (10,000원 ~ 100,000원)
python main.py --file keywords_30_40_male.txt --search-all-sites --min-price 10000 --max-price 100000 --max-results 20
```

### 5. 헤드리스 모드 (브라우저 창 숨김)
```bash
python main.py --file keywords_30_40_male.txt --search-all-sites --headless --max-results 20
```

## 포함된 키워드 카테고리

### 의류
- 셔츠, 청바지, 정장, 구두, 운동화, 가죽자켓, 후드티, 폴로셔츠, 슬랙스, 니트, 코트, 트레이닝복

### 액세서리
- 시계, 벨트, 지갑, 가방, 선글라스, 넥타이, 양말

### 전자제품
- 이어폰, 충전기, 스마트워치, 블루투스 스피커, 파워뱅크

### 건강/피트니스
- 운동화, 운동복, 보충제, 단백질, 비타민, 헬스용품

### 개인용품
- 면도기, 향수, 스킨케어, 샴푸, 로션

### 취미/레저
- 낚시용품, 캠핑용품, 골프용품, 등산용품, 자전거용품

### 자동차용품
- 차량용품, 카시트커버, 핸드폰거치대, 차량용청소기

### 생활용품
- 수건, 담요, 이불, 베개, 수납함

## 검색 후 작업

### 1. 결과 파일 병합
```bash
python main.py --merge-csv
```

### 2. 통합 파일에서 상품 등록
```bash
python main.py --register-from-file merged_results_YYYYMMDD_HHMMSS.csv --max-register-products 100
```

## 주의사항
- 검색 시간이 오래 걸릴 수 있습니다 (키워드가 많고 여러 사이트를 검색하는 경우)
- `--max-results` 옵션으로 각 키워드당 검색 결과 수를 제한할 수 있습니다
- `--headless` 옵션을 사용하면 브라우저 창이 표시되지 않습니다

