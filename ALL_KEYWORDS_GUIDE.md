# 연령대별 남녀 구매 키워드 전체 가이드

## 생성된 키워드 파일 목록

### 20대
- `keywords_20s_male.txt` - 20대 남성 구매 키워드
- `keywords_20s_female.txt` - 20대 여성 구매 키워드

### 30대
- `keywords_30_40_male.txt` - 30-40대 남성 구매 키워드
- `keywords_30s_female.txt` - 30대 여성 구매 키워드

### 40대
- `keywords_40_50_male.txt` - 40-50대 남성 구매 키워드
- `keywords_40s_female.txt` - 40대 여성 구매 키워드

### 50대
- `keywords_50s_male.txt` - 50대 남성 구매 키워드
- `keywords_50s_female.txt` - 50대 여성 구매 키워드

## 검색 실행 방법

### 1. 특정 연령대/성별 검색
```bash
# 20대 남성
python main.py --file keywords_20s_male.txt --max-results 20 --format csv

# 20대 여성
python main.py --file keywords_20s_female.txt --max-results 20 --format csv

# 30대 여성
python main.py --file keywords_30s_female.txt --max-results 20 --format csv

# 40대 여성
python main.py --file keywords_40s_female.txt --max-results 20 --format csv

# 50대 남성
python main.py --file keywords_50s_male.txt --max-results 20 --format csv

# 50대 여성
python main.py --file keywords_50s_female.txt --max-results 20 --format csv
```

### 2. 모든 사이트에서 검색
```bash
python main.py --file keywords_20s_male.txt --search-all-sites --max-results 20 --format csv
```

### 3. 여러 파일 동시 검색 (배치 처리)
Windows PowerShell에서:
```powershell
$files = @("keywords_20s_male.txt", "keywords_20s_female.txt", "keywords_30s_female.txt")
foreach ($file in $files) {
    python main.py --file $file --max-results 20 --format csv
}
```

## 연령대별 특징

### 20대
**남성**: 캐주얼 의류, 게임용품, 운동용품, 전자제품
**여성**: 트렌디 의류, 화장품, 액세서리, 셀카용품

### 30대
**남성**: 비즈니스 의류, 건강용품, 전자제품, 운동용품
**여성**: 정장, 안티에이징 화장품, 건강용품, 실용적 제품

### 40대
**남성**: 정장 중심, 건강 모니터링, 취미용품, 자동차용품
**여성**: 고급 의류, 안티에이징, 건강식품, 실용적 제품

### 50대
**남성**: 건강관리, 취미활동, 실용적 제품, 보조기
**여성**: 건강관리, 갱년기 영양제, 안티에이징, 실용적 제품

## 키워드 통계

| 연령대 | 남성 키워드 수 | 여성 키워드 수 |
|--------|---------------|---------------|
| 20대 | ~80개 | ~100개 |
| 30대 | ~70개 | ~90개 |
| 40대 | ~150개 | ~120개 |
| 50대 | ~150개 | ~130개 |

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
- 각 연령대별로 키워드 수가 많아 검색 시간이 오래 걸릴 수 있습니다
- `--max-results` 옵션으로 각 키워드당 검색 결과 수를 제한하세요
- `--headless` 옵션을 사용하면 브라우저 창이 표시되지 않습니다
- 여러 파일을 연속으로 검색할 경우 시간이 오래 걸릴 수 있으니 주의하세요

