"""
인기 키워드 수집 모듈
외부 사이트(네이버 쇼핑, 쿠팡, 아이템 스카우트)에서 인기 키워드 수집
"""
from typing import List, Optional, Set, Dict, Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
import requests
from collections import Counter
from bs4 import BeautifulSoup

from config import BASE_URL, WAIT_TIMES, DEFAULT_TIMEOUT, USER_AGENT
from logger import default_logger as logger
from brand_filter import (
    filter_brand_keywords, 
    get_non_brand_keywords,
    analyze_competition,
    is_brand_keyword
)

# 외부 사이트 URL
NAVER_SHOPPING_URL = "https://shopping.naver.com"
NAVER_DATALAB_URL = "https://datalab.naver.com"
NAVER_SHOPPING_INSIGHT_URL = "https://shopping.naver.com/insight"
COUPANG_BESTSELLER_URL = "https://www.coupang.com/np/categories"
COUPANG_TREND_URL = "https://www.coupang.com/np/trend"
ITEM_SCOUT_URL = "https://itemscout.io"
ITEM_SCOUT_KEYWORD_URL = "https://itemscout.io/keyword"  # 키워드 분석 페이지
GMARKET_TREND_URL = "http://www.gmarket.co.kr/n/best"
AUCTION_TREND_URL = "http://www.auction.co.kr"
ELEVENST_TREND_URL = "http://www.11st.co.kr/browsing/BestSeller.tmall"
GOOGLE_TRENDS_URL = "https://trends.google.co.kr/trending"
SELLERIUM_URL = "https://sellerium.com"

def get_trending_keywords(
    driver: Optional[WebDriver] = None,
    method: str = 'auto',
    max_keywords: int = 10,
    source: str = 'products',
    exclude_brands: bool = False,
    analyze_competition_data: bool = False
) -> List[str]:
    """
    인기 키워드 수집
    
    Args:
        driver: WebDriver 객체 (None이면 requests 사용)
        method: 수집 방법 ('auto', 'products', 'search_suggestions', 'categories', 
                'naver', 'coupang', 'itemscout')
        max_keywords: 최대 키워드 수
        source: 키워드 소스 (위와 동일)
        exclude_brands: 브랜드 키워드 제외 여부
        analyze_competition_data: 경쟁 분석 데이터 포함 여부
    
    Returns:
        키워드 리스트 또는 분석 결과 리스트
    """
    try:
        # 외부 사이트에서 수집
        if method == 'naver' or source == 'naver':
            keywords = _get_keywords_from_naver(max_keywords)
            if keywords:
                logger.info(f"네이버 쇼핑에서 {len(keywords)}개 키워드 추출")
                keywords = keywords[:max_keywords]
                if exclude_brands:
                    keywords = filter_brand_keywords(keywords)
                    logger.info(f"브랜드 제외 후 {len(keywords)}개 키워드")
                return keywords
        
        if method == 'coupang' or source == 'coupang':
            keywords = _get_keywords_from_coupang(driver, max_keywords)
            if keywords:
                logger.info(f"쿠팡에서 {len(keywords)}개 키워드 추출")
                keywords = keywords[:max_keywords]
                if exclude_brands:
                    keywords = filter_brand_keywords(keywords)
                    logger.info(f"브랜드 제외 후 {len(keywords)}개 키워드")
                return keywords
        
        if method == 'itemscout' or source == 'itemscout':
            keywords, competition_data = _get_keywords_from_itemscout_with_analysis(
                driver, max_keywords, analyze_competition_data
            )
            if keywords:
                logger.info(f"아이템 스카우트에서 {len(keywords)}개 키워드 추출")
                keywords = keywords[:max_keywords]
                if exclude_brands:
                    original_count = len(keywords)
                    keywords = filter_brand_keywords(keywords)
                    logger.info(f"브랜드 제외 후 {len(keywords)}개 키워드 (제외: {original_count - len(keywords)}개)")
                return keywords
        
        if method == 'gmarket' or source == 'gmarket':
            keywords = _get_keywords_from_gmarket(max_keywords)
            if keywords:
                logger.info(f"지마켓에서 {len(keywords)}개 키워드 추출")
                keywords = keywords[:max_keywords]
                if exclude_brands:
                    keywords = filter_brand_keywords(keywords)
                    logger.info(f"브랜드 제외 후 {len(keywords)}개 키워드")
                return keywords
        
        if method == '11st' or source == '11st':
            keywords = _get_keywords_from_11st(max_keywords)
            if keywords:
                logger.info(f"11번가에서 {len(keywords)}개 키워드 추출")
                keywords = keywords[:max_keywords]
                if exclude_brands:
                    keywords = filter_brand_keywords(keywords)
                    logger.info(f"브랜드 제외 후 {len(keywords)}개 키워드")
                return keywords
        
        if method == 'google' or source == 'google':
            keywords = _get_keywords_from_google_trends(driver, max_keywords)
            if keywords:
                logger.info(f"구글 트렌드에서 {len(keywords)}개 키워드 추출")
                keywords = keywords[:max_keywords]
                if exclude_brands:
                    keywords = filter_brand_keywords(keywords)
                    logger.info(f"브랜드 제외 후 {len(keywords)}개 키워드")
                return keywords
        
        # 도매꾹 사이트에서 수집 (기존 방법)
        if driver:
            if method == 'auto' or source == 'products':
                keywords = _extract_keywords_from_popular_products(driver, max_keywords)
                if keywords:
                    logger.info(f"인기 상품에서 {len(keywords)}개 키워드 추출")
                    keywords = keywords[:max_keywords]
                    if exclude_brands:
                        keywords = filter_brand_keywords(keywords)
                    return keywords
            
            if method == 'auto' or source == 'search_suggestions':
                keywords = _extract_keywords_from_search_suggestions(driver, max_keywords)
                if keywords:
                    logger.info(f"검색 제안에서 {len(keywords)}개 키워드 추출")
                    keywords = keywords[:max_keywords]
                    if exclude_brands:
                        keywords = filter_brand_keywords(keywords)
                    return keywords
            
            if method == 'auto' or source == 'categories':
                keywords = _extract_keywords_from_categories(driver, max_keywords)
                if keywords:
                    logger.info(f"카테고리에서 {len(keywords)}개 키워드 추출")
                    keywords = keywords[:max_keywords]
                    if exclude_brands:
                        keywords = filter_brand_keywords(keywords)
                    return keywords
        
        # 기본값: 일반적인 인기 키워드 반환
        logger.warning("인기 키워드를 자동으로 찾지 못했습니다. 기본 키워드를 사용합니다.")
        keywords = _get_default_trending_keywords()[:max_keywords]
        if exclude_brands:
            keywords = filter_brand_keywords(keywords)
        return keywords
        
    except Exception as e:
        logger.error(f"인기 키워드 수집 실패: {e}", exc_info=True)
        return _get_default_trending_keywords()[:max_keywords]

def _extract_keywords_from_popular_products(
    driver: WebDriver,
    max_keywords: int
) -> List[str]:
    """인기 상품 목록에서 키워드 추출"""
    try:
        logger.info("인기 상품 목록 페이지 접근 중...")
        driver.get(BASE_URL)
        
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(WAIT_TIMES['page_load'])
        
        # 인기 상품 섹션 찾기
        product_keywords = []
        
        # 여러 선택자로 상품명 찾기
        product_selectors = [
            ".sub_cont_bane1 .itemName",
            ".sub_cont_bane1 .main_cont_text1",
            ".item .name",
            "[class*='item'] [class*='name']",
            ".product-name",
        ]
        
        product_names = []
        for selector in product_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements[:50]:  # 최대 50개만
                    text = elem.text.strip()
                    if text and len(text) > 2:
                        product_names.append(text)
                if product_names:
                    break
            except:
                continue
        
        if not product_names:
            logger.warning("상품명을 찾을 수 없습니다.")
            return []
        
        # 상품명에서 키워드 추출
        keywords = _extract_keywords_from_texts(product_names, max_keywords)
        return keywords
        
    except Exception as e:
        logger.debug(f"인기 상품에서 키워드 추출 실패: {e}")
        return []

def _extract_keywords_from_search_suggestions(
    driver: WebDriver,
    max_keywords: int
) -> List[str]:
    """검색 자동완성/인기 검색어에서 키워드 추출"""
    try:
        logger.info("검색 제안 키워드 수집 중...")
        driver.get(BASE_URL)
        
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(WAIT_TIMES['page_load'])
        
        # 검색창 찾기
        search_input = driver.find_element(By.CSS_SELECTOR, "input[name='sw']")
        if not search_input:
            return []
        
        # 검색창에 공백 입력하여 자동완성 트리거 시도
        search_input.click()
        time.sleep(0.5)
        
        # 자동완성 드롭다운 찾기
        suggestions = []
        suggestion_selectors = [
            ".autocomplete li",
            ".search-suggestions li",
            "[class*='suggestion']",
            "[class*='autocomplete'] a",
        ]
        
        for selector in suggestion_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements[:20]:
                    text = elem.text.strip()
                    if text:
                        suggestions.append(text)
                if suggestions:
                    break
            except:
                continue
        
        if suggestions:
            return suggestions[:max_keywords]
        
        return []
        
    except Exception as e:
        logger.debug(f"검색 제안에서 키워드 추출 실패: {e}")
        return []

def _extract_keywords_from_categories(
    driver: WebDriver,
    max_keywords: int
) -> List[str]:
    """카테고리별 인기 상품에서 키워드 추출"""
    try:
        logger.info("카테고리별 인기 상품 키워드 수집 중...")
        
        # 카테고리 링크 찾기
        category_selectors = [
            ".category a",
            ".nav-category a",
            "[class*='category'] a",
            ".menu-category a",
        ]
        
        categories = []
        for selector in category_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements[:20]:
                    text = elem.text.strip()
                    if text and len(text) > 1:
                        categories.append(text)
                if categories:
                    break
            except:
                continue
        
        return categories[:max_keywords]
        
    except Exception as e:
        logger.debug(f"카테고리에서 키워드 추출 실패: {e}")
        return []

def _extract_keywords_from_texts(texts: List[str], max_keywords: int) -> List[str]:
    """텍스트 리스트에서 키워드 추출"""
    # 불용어 제거
    stopwords = {
        '도매꾹판매가', '원', '개', '이상', '구매', '바로가기', '판매가',
        'NEW', 'new', 'NEW!', '특가', '할인', '세일', '무료배송',
        '품절', '재고', '수량', '개수', '상품', '제품', '아이템'
    }
    
    # 키워드 추출
    all_keywords = []
    for text in texts:
        # 한글, 영문, 숫자만 추출
        words = re.findall(r'[가-힣]+|[a-zA-Z]+|\d+', text)
        for word in words:
            word = word.strip()
            # 2글자 이상이고 불용어가 아닌 경우만
            if len(word) >= 2 and word not in stopwords:
                all_keywords.append(word)
    
    # 빈도수 계산
    keyword_counts = Counter(all_keywords)
    
    # 빈도수 높은 순으로 정렬
    sorted_keywords = [kw for kw, count in keyword_counts.most_common(max_keywords * 2)]
    
    # 중복 제거 및 반환
    seen = set()
    result = []
    for kw in sorted_keywords:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
            if len(result) >= max_keywords:
                break
    
    return result

def _get_default_trending_keywords() -> List[str]:
    """기본 인기 키워드 반환"""
    return [
        '양말', '장갑', '모자', '마스크', '마스크팩',
        '스티커', '스티커북', '색연필', '크레파스', '물감',
        '가방', '지갑', '키링', '핸드폰케이스', '충전기',
        '텀블러', '물병', '컵', '접시', '수저',
        '장난감', '인형', '블록', '퍼즐', '보드게임',
        '문구', '노트', '펜', '연필', '지우개',
        '화장품', '스킨케어', '마스크팩', '립밤', '선크림',
        '의류', '티셔츠', '후드', '바지', '치마',
        '신발', '운동화', '슬리퍼', '부츠', '샌들',
        '악세서리', '목걸이', '귀걸이', '반지', '팔찌',
        '홈데코', '인테리어', '조명', '커튼', '카펫',
        '주방용품', '냄비', '프라이팬', '도마', '행주',
        '청소용품', '걸레', '청소기', '빗자루', '휴지',
        '욕실용품', '수건', '비누', '샴푸', '바디워시',
    ]

def _get_keywords_from_naver(max_keywords: int) -> List[str]:
    """
    네이버 쇼핑/데이터랩에서 인기 키워드 수집
    
    방법:
    1. 네이버 쇼핑 베스트 페이지에서 상품명 추출
    2. 네이버 데이터랩 인기 검색어 (API 사용 가능)
    """
    try:
        logger.info("네이버 쇼핑에서 인기 키워드 수집 중...")
        
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        # 네이버 쇼핑 베스트 페이지
        best_urls = [
            "https://shopping.naver.com/best/home",
            "https://shopping.naver.com/category/category.naver",
        ]
        
        all_keywords = []
        
        for url in best_urls:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 상품명 추출 (여러 선택자 시도)
                    product_selectors = [
                        '.product_title',
                        '.productName',
                        '[class*="product"] [class*="name"]',
                        '[class*="item"] [class*="title"]',
                        'a[href*="/products/"]',
                    ]
                    
                    product_names = []
                    for selector in product_selectors:
                        elements = soup.select(selector)
                        for elem in elements[:max(100, max_keywords * 3)]:  # 더 많이 수집
                            text = elem.get_text(strip=True)
                            if text and len(text) > 2:
                                product_names.append(text)
                        if product_names:
                            break
                    
                    if product_names:
                        keywords = _extract_keywords_from_texts(product_names, max_keywords * 3)
                        all_keywords.extend(keywords)
                        break
            except Exception as e:
                logger.debug(f"네이버 쇼핑 페이지 접근 실패 ({url}): {e}")
                continue
        
        if all_keywords:
            # 중복 제거
            seen = set()
            result = []
            for kw in all_keywords:
                if kw not in seen:
                    seen.add(kw)
                    result.append(kw)
                    if len(result) >= max_keywords:
                        break
            return result
        
        return []
        
    except Exception as e:
        logger.debug(f"네이버에서 키워드 수집 실패: {e}")
        return []

def _get_keywords_from_coupang(driver: Optional[WebDriver], max_keywords: int) -> List[str]:
    """
    쿠팡 베스트셀러에서 인기 키워드 수집
    
    방법:
    1. 쿠팡 베스트셀러 페이지에서 상품명 추출
    2. 카테고리별 베스트 상품명 추출
    """
    try:
        logger.info("쿠팡에서 인기 키워드 수집 중...")
        
        if driver:
            # Selenium 사용
            try:
                driver.get(COUPANG_BESTSELLER_URL)
                WebDriverWait(driver, DEFAULT_TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(WAIT_TIMES['page_load'])
                
                # 상품명 추출
                product_selectors = [
                    ".name",
                    "[class*='product'] [class*='name']",
                    "[class*='item'] [class*='title']",
                    "dd.name",
                ]
                
                product_names = []
                for selector in product_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements[:max(100, max_keywords * 3)]:  # 더 많이 수집
                            text = elem.text.strip()
                            if text and len(text) > 2:
                                product_names.append(text)
                        if product_names:
                            break
                    except:
                        continue
                
                if product_names:
                    keywords = _extract_keywords_from_texts(product_names, max_keywords * 3)
                    return keywords
            except Exception as e:
                logger.debug(f"Selenium으로 쿠팡 접근 실패: {e}")
        
        # requests 사용 (대안)
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        }
        
        try:
            response = requests.get(COUPANG_BESTSELLER_URL, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                product_names = []
                # 쿠팡 상품명 선택자
                for elem in soup.select('.name, [class*="product-name"], [class*="item-title"]')[:max(100, max_keywords * 3)]:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 2:
                        product_names.append(text)
                
                if product_names:
                    keywords = _extract_keywords_from_texts(product_names, max_keywords * 3)
                    return keywords
        except Exception as e:
            logger.debug(f"requests로 쿠팡 접근 실패: {e}")
        
        return []
        
    except Exception as e:
        logger.debug(f"쿠팡에서 키워드 수집 실패: {e}")
        return []

def _get_keywords_from_itemscout_with_analysis(
    driver: Optional[WebDriver], 
    max_keywords: int,
    analyze_competition_data: bool = False
) -> Tuple[List[str], Dict]:
    """
    아이템 스카우트에서 인기 키워드 수집 및 경쟁 분석
    
    방법:
    1. 키워드 분석 페이지(/keyword)의 트렌드 키워드 테이블에서 추출
    2. 일간/주간 트렌드 키워드 테이블에서 키워드 컬럼 추출
    3. 검색수, 상품수, 경쟁강도 등 지표 수집
    
    수집 기준:
    - 일간 트렌드 키워드 테이블의 키워드 컬럼
    - 주간 트렌드 키워드 테이블의 키워드 컬럼
    - 검색수, 상품수, 경쟁강도 등 지표 포함
    
    Returns:
        (키워드 리스트, 경쟁 데이터 딕셔너리) 튜플
    """
    try:
        logger.info("아이템 스카우트에서 인기 키워드 수집 및 경쟁 분석 중...")
        
        if not driver:
            logger.warning("아이템 스카우트는 Selenium이 필요합니다.")
            return [], {}
        
        # 아이템 스카우트 키워드 분석 페이지
        url = ITEM_SCOUT_KEYWORD_URL
        
        try:
            driver.get(url)
            WebDriverWait(driver, DEFAULT_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(WAIT_TIMES['page_load'] * 2)  # 동적 콘텐츠 로딩 대기
            
            keywords = []
            competition_data = {}
            
            # 방법 1: 트렌드 키워드 테이블에서 추출 (경쟁 데이터 포함)
            # 일간 트렌드 키워드 테이블 찾기
            try:
                # 테이블 찾기
                tables = driver.find_elements(By.CSS_SELECTOR, "table")
                
                for table in tables:
                    rows = table.find_elements(By.CSS_SELECTOR, "tr")
                    if len(rows) < 2:
                        continue
                    
                    # 헤더 확인
                    header = rows[0]
                    header_cells = header.find_elements(By.CSS_SELECTOR, "th, td")
                    
                    # 컬럼 인덱스 찾기
                    keyword_idx = None
                    search_idx = None
                    product_idx = None
                    competition_idx = None
                    
                    for idx, cell in enumerate(header_cells):
                        text = cell.text.strip().lower()
                        if '키워드' in text or 'keyword' in text:
                            keyword_idx = idx
                        elif '검색' in text or 'search' in text:
                            search_idx = idx
                        elif '상품' in text or 'product' in text:
                            product_idx = idx
                        elif '경쟁' in text or 'competition' in text:
                            competition_idx = idx
                    
                    # 데이터 행 파싱
                    for row in rows[1:max_keywords + 1]:
                        cells = row.find_elements(By.CSS_SELECTOR, "td")
                        if len(cells) < 3:
                            continue
                        
                        # 키워드 추출
                        if keyword_idx is not None and keyword_idx < len(cells):
                            keyword_text = cells[keyword_idx].text.strip()
                        else:
                            keyword_text = cells[2].text.strip() if len(cells) > 2 else ""
                        
                        if keyword_text and len(keyword_text) >= 2:
                            keyword_text = re.sub(r'\s+', ' ', keyword_text).strip()
                            
                            # 경쟁 데이터 수집
                            if analyze_competition_data:
                                comp_data = {}
                                
                                if search_idx is not None and search_idx < len(cells):
                                    search_text = cells[search_idx].text.strip()
                                    comp_data['search_count'] = _parse_number(search_text)
                                
                                if product_idx is not None and product_idx < len(cells):
                                    product_text = cells[product_idx].text.strip()
                                    comp_data['product_count'] = _parse_number(product_text)
                                
                                if competition_idx is not None and competition_idx < len(cells):
                                    comp_text = cells[competition_idx].text.strip()
                                    comp_data['competition_ratio'] = _parse_float(comp_text)
                                
                                if comp_data:
                                    competition_data[keyword_text] = comp_data
                            
                            if keyword_text not in keywords:
                                keywords.append(keyword_text)
                    
                    if keywords:
                        break
                
                logger.debug(f"트렌드 테이블에서 {len(keywords)}개 키워드 추출")
            except Exception as e:
                logger.debug(f"트렌드 테이블 파싱 실패: {e}")
            
            # 방법 2: CSS 선택자로 키워드 찾기
            if len(keywords) < max_keywords:
                try:
                    # 테이블 내의 모든 텍스트에서 키워드 추출
                    tables = driver.find_elements(By.CSS_SELECTOR, "table")
                    for table in tables:
                        rows = table.find_elements(By.CSS_SELECTOR, "tr")
                        for row in rows[1:]:  # 헤더 제외
                            cells = row.find_elements(By.CSS_SELECTOR, "td")
                            if len(cells) >= 3:
                                # 3번째 셀이 키워드일 가능성이 높음
                                keyword_text = cells[2].text.strip()
                                if keyword_text and len(keyword_text) >= 2:
                                    # 숫자만 있는 경우 제외
                                    if not keyword_text.replace(',', '').isdigit():
                                        keyword_text = re.sub(r'\s+', ' ', keyword_text).strip()
                                        if keyword_text and keyword_text not in keywords:
                                            keywords.append(keyword_text)
                                        if len(keywords) >= max_keywords * 2:
                                            break
                        if len(keywords) >= max_keywords * 2:
                            break
                except Exception as e:
                    logger.debug(f"CSS 선택자로 키워드 추출 실패: {e}")
            
            # 방법 3: 특정 클래스나 속성으로 키워드 찾기
            if len(keywords) < max_keywords:
                try:
                    # 키워드가 포함된 요소 찾기
                    keyword_elements = driver.find_elements(
                        By.XPATH,
                        "//*[contains(@class, 'keyword') or contains(text(), '자라') or contains(text(), '케이스티파이')]"
                    )
                    for elem in keyword_elements[:max_keywords * 3]:
                        text = elem.text.strip()
                        # 테이블 셀 내의 키워드만 추출
                        if text and len(text) >= 2 and len(text) <= 50:
                            # 숫자만 있는 경우 제외
                            if not text.replace(',', '').replace('.', '').isdigit():
                                text = re.sub(r'\s+', ' ', text).strip()
                                if text and text not in keywords:
                                    keywords.append(text)
                except Exception as e:
                    logger.debug(f"XPath로 키워드 추출 실패: {e}")
            
            # 중복 제거 및 정리
            seen = set()
            result = []
            for kw in keywords:
                kw_clean = kw.strip()
                # 한글, 영문, 숫자만 포함된 키워드만 선택
                if (kw_clean and 
                    len(kw_clean) >= 2 and 
                    len(kw_clean) <= 30 and
                    re.match(r'^[가-힣a-zA-Z0-9\s]+$', kw_clean) and
                    kw_clean.lower() not in seen):
                    seen.add(kw_clean.lower())
                    result.append(kw_clean)
                    if len(result) >= max_keywords:
                        break
            
            if result:
                logger.info(f"아이템 스카우트에서 {len(result)}개 키워드 추출 성공")
                if competition_data:
                    logger.info(f"경쟁 분석 데이터 {len(competition_data)}개 수집")
                return result, competition_data
            
            logger.warning("아이템 스카우트에서 키워드를 찾지 못했습니다.")
            return [], {}
                    
        except Exception as e:
            logger.debug(f"아이템 스카우트 페이지 접근 실패: {e}")
            return [], {}
        
    except Exception as e:
        logger.debug(f"아이템 스카우트에서 키워드 수집 실패: {e}")
        return [], {}

def _parse_number(text: str) -> int:
    """텍스트에서 숫자 추출 (콤마 제거)"""
    try:
        cleaned = text.replace(',', '').replace(' ', '')
        return int(cleaned)
    except:
        return 0

def _parse_float(text: str) -> float:
    """텍스트에서 실수 추출"""
    try:
        cleaned = text.replace(',', '').replace(' ', '')
        return float(cleaned)
    except:
        return 0.0

# 기존 함수 호환성을 위한 래퍼
def _get_keywords_from_itemscout(driver: Optional[WebDriver], max_keywords: int) -> List[str]:
    """기존 호환성을 위한 래퍼 함수"""
    keywords, _ = _get_keywords_from_itemscout_with_analysis(driver, max_keywords, False)
    return keywords

def get_keywords_from_result_files(result_dir: str = "result", max_keywords: int = 10) -> List[str]:
    """
    과거 검색 결과 파일에서 자주 나오는 키워드 추출
    
    Args:
        result_dir: 결과 파일이 있는 디렉토리
        max_keywords: 최대 키워드 수
    
    Returns:
        키워드 리스트
    """
    import os
    import json
    from collections import Counter
    
    try:
        if not os.path.exists(result_dir):
            return []
        
        all_keywords = []
        
        # JSON 파일 읽기
        for filename in os.listdir(result_dir):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(result_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if isinstance(data, list):
                        for item in data:
                            # 상품명에서 키워드 추출
                            name = item.get('name', '')
                            if name:
                                keywords = re.findall(r'[가-힣]+', name)
                                all_keywords.extend([kw for kw in keywords if len(kw) >= 2])
            except:
                continue
        
        if not all_keywords:
            return []
        
        # 빈도수 계산
        keyword_counts = Counter(all_keywords)
        
        # 상위 키워드 반환
        return [kw for kw, count in keyword_counts.most_common(max_keywords)]
        
    except Exception as e:
        logger.debug(f"결과 파일에서 키워드 추출 실패: {e}")
        return []

def get_trending_keywords_from_multiple_sources(
    driver: Optional[WebDriver] = None,
    max_keywords: int = 50,
    exclude_brands: bool = False,
    analyze_competition_data: bool = False
) -> List[str]:
    """
    여러 소스를 동시에 활용하여 인기 키워드 수집
    
    여러 소스(네이버, 쿠팡, 아이템스카우트, 지마켓, 옥션, 11번가 등)에서 키워드를 수집하여
    중복을 제거하고 품질이 높은 키워드를 반환합니다.
    
    Args:
        driver: WebDriver 객체
        max_keywords: 최대 키워드 수
        exclude_brands: 브랜드 키워드 제외 여부
        analyze_competition_data: 경쟁 분석 데이터 포함 여부
    
    Returns:
        키워드 리스트
    """
    all_keywords = []
    sources_used = []
    
    # 각 소스에서 키워드 수집 (소스당 더 많이 수집)
    per_source_count = max(max_keywords // 8, 15)  # 소스당 최소 15개 (더 많은 소스 지원)
    
    logger.info(f"여러 소스에서 키워드 수집 시작 (목표: {max_keywords}개, 소스당: {per_source_count}개)")
    
    # 1. 네이버 쇼핑에서 수집
    try:
        logger.info("[1/8] 네이버 쇼핑에서 키워드 수집 중...")
        naver_keywords = _get_keywords_from_naver(per_source_count * 2)
        if naver_keywords:
            all_keywords.extend(naver_keywords)
            sources_used.append(f"네이버({len(naver_keywords)}개)")
            logger.info(f"  ✓ 네이버에서 {len(naver_keywords)}개 키워드 수집")
    except Exception as e:
        logger.debug(f"네이버 키워드 수집 실패: {e}")
    
    # 2. 네이버 데이터랩에서 수집
    try:
        logger.info("[2/8] 네이버 데이터랩에서 키워드 수집 중...")
        naver_datalab_keywords = _get_keywords_from_naver_datalab(per_source_count * 2)
        if naver_datalab_keywords:
            all_keywords.extend(naver_datalab_keywords)
            sources_used.append(f"네이버데이터랩({len(naver_datalab_keywords)}개)")
            logger.info(f"  ✓ 네이버 데이터랩에서 {len(naver_datalab_keywords)}개 키워드 수집")
    except Exception as e:
        logger.debug(f"네이버 데이터랩 키워드 수집 실패: {e}")
    
    # 3. 쿠팡에서 수집
    try:
        logger.info("[3/8] 쿠팡에서 키워드 수집 중...")
        coupang_keywords = _get_keywords_from_coupang(driver, per_source_count * 2)
        if coupang_keywords:
            all_keywords.extend(coupang_keywords)
            sources_used.append(f"쿠팡({len(coupang_keywords)}개)")
            logger.info(f"  ✓ 쿠팡에서 {len(coupang_keywords)}개 키워드 수집")
    except Exception as e:
        logger.debug(f"쿠팡 키워드 수집 실패: {e}")
    
    # 4. 쿠팡 트렌드에서 수집
    if driver:
        try:
            logger.info("[4/8] 쿠팡 트렌드에서 키워드 수집 중...")
            coupang_trend_keywords = _get_keywords_from_coupang_trend(driver, per_source_count * 2)
            if coupang_trend_keywords:
                all_keywords.extend(coupang_trend_keywords)
                sources_used.append(f"쿠팡트렌드({len(coupang_trend_keywords)}개)")
                logger.info(f"  ✓ 쿠팡 트렌드에서 {len(coupang_trend_keywords)}개 키워드 수집")
        except Exception as e:
            logger.debug(f"쿠팡 트렌드 키워드 수집 실패: {e}")
    
    # 5. 아이템스카우트에서 수집
    if driver:
        try:
            logger.info("[5/8] 아이템스카우트에서 키워드 수집 중...")
            itemscout_keywords, _ = _get_keywords_from_itemscout_with_analysis(
                driver, per_source_count * 2, analyze_competition_data
            )
            if itemscout_keywords:
                all_keywords.extend(itemscout_keywords)
                sources_used.append(f"아이템스카우트({len(itemscout_keywords)}개)")
                logger.info(f"  ✓ 아이템스카우트에서 {len(itemscout_keywords)}개 키워드 수집")
        except Exception as e:
            logger.debug(f"아이템스카우트 키워드 수집 실패: {e}")
    
    # 6. 지마켓에서 수집
    try:
        logger.info("[6/8] 지마켓에서 키워드 수집 중...")
        gmarket_keywords = _get_keywords_from_gmarket(per_source_count * 2)
        if gmarket_keywords:
            all_keywords.extend(gmarket_keywords)
            sources_used.append(f"지마켓({len(gmarket_keywords)}개)")
            logger.info(f"  ✓ 지마켓에서 {len(gmarket_keywords)}개 키워드 수집")
    except Exception as e:
        logger.debug(f"지마켓 키워드 수집 실패: {e}")
    
    # 7. 11번가에서 수집
    try:
        logger.info("[7/8] 11번가에서 키워드 수집 중...")
        elevenst_keywords = _get_keywords_from_11st(per_source_count * 2)
        if elevenst_keywords:
            all_keywords.extend(elevenst_keywords)
            sources_used.append(f"11번가({len(elevenst_keywords)}개)")
            logger.info(f"  ✓ 11번가에서 {len(elevenst_keywords)}개 키워드 수집")
    except Exception as e:
        logger.debug(f"11번가 키워드 수집 실패: {e}")
    
    # 8. 구글 트렌드에서 수집
    if driver:
        try:
            logger.info("[8/8] 구글 트렌드에서 키워드 수집 중...")
            google_trends_keywords = _get_keywords_from_google_trends(driver, per_source_count * 2)
            if google_trends_keywords:
                all_keywords.extend(google_trends_keywords)
                sources_used.append(f"구글트렌드({len(google_trends_keywords)}개)")
                logger.info(f"  ✓ 구글 트렌드에서 {len(google_trends_keywords)}개 키워드 수집")
        except Exception as e:
            logger.debug(f"구글 트렌드 키워드 수집 실패: {e}")
    
    if not all_keywords:
        logger.warning("모든 소스에서 키워드를 찾지 못했습니다. 기본 키워드를 사용합니다.")
        return _get_default_trending_keywords()[:max_keywords]
    
    logger.info(f"\n총 {len(all_keywords)}개 키워드 수집 완료 (소스: {', '.join(sources_used)})")
    
    # 중복 제거 및 품질 필터링
    logger.info("중복 제거 및 품질 필터링 중...")
    
    # 키워드 정리 및 중복 제거
    seen = set()
    cleaned_keywords = []
    
    for kw in all_keywords:
        kw_clean = kw.strip()
        # 품질 필터링: 2-30자, 한글/영문/숫자만, 불용어 제외
        if (kw_clean and 
            2 <= len(kw_clean) <= 30 and
            re.match(r'^[가-힣a-zA-Z0-9\s]+$', kw_clean) and
            kw_clean.lower() not in seen):
            seen.add(kw_clean.lower())
            cleaned_keywords.append(kw_clean)
    
    logger.info(f"중복 제거 후 {len(cleaned_keywords)}개 키워드")
    
    # 빈도수 기반 정렬 (여러 소스에서 나온 키워드가 우선)
    if len(cleaned_keywords) > max_keywords:
        keyword_counts = Counter(all_keywords)
        # 빈도수와 함께 정렬
        scored_keywords = []
        for kw in cleaned_keywords:
            score = keyword_counts.get(kw, 0)
            scored_keywords.append((score, kw))
        
        # 빈도수 높은 순으로 정렬
        scored_keywords.sort(reverse=True)
        cleaned_keywords = [kw for _, kw in scored_keywords[:max_keywords]]
    
    # 브랜드 필터링
    if exclude_brands:
        original_count = len(cleaned_keywords)
        cleaned_keywords = filter_brand_keywords(cleaned_keywords)
        logger.info(f"브랜드 제외 후 {len(cleaned_keywords)}개 키워드 (제외: {original_count - len(cleaned_keywords)}개)")
    
    # 최종 결과 제한
    final_keywords = cleaned_keywords[:max_keywords]
    
    logger.info(f"\n최종 {len(final_keywords)}개 키워드 선정 완료")
    
    return final_keywords

def _get_keywords_from_naver_datalab(max_keywords: int) -> List[str]:
    """
    네이버 데이터랩에서 인기 키워드 수집
    """
    try:
        logger.info("네이버 데이터랩에서 키워드 수집 중...")
        
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        }
        
        # 네이버 데이터랩 쇼핑 인사이트
        urls = [
            "https://datalab.naver.com/shoppingInsight/sCategory.naver",
            "https://datalab.naver.com/keyword/realtimeList.naver",
        ]
        
        all_keywords = []
        for url in urls:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 키워드 추출 (다양한 선택자 시도)
                    keyword_selectors = [
                        '.keyword',
                        '.rank',
                        '[class*="keyword"]',
                        '[class*="rank"]',
                        'a[href*="keyword"]',
                        '.list_item',
                    ]
                    
                    keywords = []
                    for selector in keyword_selectors:
                        elements = soup.select(selector)
                        for elem in elements[:max_keywords]:
                            text = elem.get_text(strip=True)
                            if text and 2 <= len(text) <= 30:
                                keywords.append(text)
                        if keywords:
                            break
                    
                    if keywords:
                        all_keywords.extend(keywords)
                        break
            except Exception as e:
                logger.debug(f"네이버 데이터랩 페이지 접근 실패 ({url}): {e}")
                continue
        
        if all_keywords:
            # 중복 제거
            seen = set()
            result = []
            for kw in all_keywords:
                kw_clean = kw.strip()
                if kw_clean.lower() not in seen:
                    seen.add(kw_clean.lower())
                    result.append(kw_clean)
                    if len(result) >= max_keywords:
                        break
            return result
        
        return []
    except Exception as e:
        logger.debug(f"네이버 데이터랩에서 키워드 수집 실패: {e}")
        return []

def _get_keywords_from_coupang_trend(driver: Optional[WebDriver], max_keywords: int) -> List[str]:
    """
    쿠팡 트렌드 페이지에서 키워드 수집
    """
    try:
        logger.info("쿠팡 트렌드에서 키워드 수집 중...")
        
        if not driver:
            return []
        
        driver.get(COUPANG_TREND_URL)
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(WAIT_TIMES['page_load'])
        
        # 트렌드 키워드 추출
        keyword_selectors = [
            ".trend-keyword",
            "[class*='trend']",
            "[class*='keyword']",
            ".product-name",
            ".name",
        ]
        
        keywords = []
        for selector in keyword_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements[:max_keywords]:
                    text = elem.text.strip()
                    if text and 2 <= len(text) <= 30:
                        keywords.append(text)
                if keywords:
                    break
            except:
                continue
        
        if keywords:
            return keywords[:max_keywords]
        
        return []
    except Exception as e:
        logger.debug(f"쿠팡 트렌드에서 키워드 수집 실패: {e}")
        return []

def _get_keywords_from_gmarket(max_keywords: int) -> List[str]:
    """
    지마켓 베스트 상품에서 키워드 수집
    """
    try:
        logger.info("지마켓에서 키워드 수집 중...")
        
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        }
        
        try:
            response = requests.get(GMARKET_TREND_URL, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 상품명 추출
                product_selectors = [
                    '.item_title',
                    '.title',
                    '[class*="item"] [class*="title"]',
                    '[class*="product"] [class*="name"]',
                    'a[href*="/item/"]',
                ]
                
                product_names = []
                for selector in product_selectors:
                    elements = soup.select(selector)
                    for elem in elements[:max(100, max_keywords * 3)]:
                        text = elem.get_text(strip=True)
                        if text and len(text) > 2:
                            product_names.append(text)
                    if product_names:
                        break
                
                if product_names:
                    keywords = _extract_keywords_from_texts(product_names, max_keywords * 3)
                    return keywords
        except Exception as e:
            logger.debug(f"지마켓 페이지 접근 실패: {e}")
        
        return []
    except Exception as e:
        logger.debug(f"지마켓에서 키워드 수집 실패: {e}")
        return []

def _get_keywords_from_11st(max_keywords: int) -> List[str]:
    """
    11번가 베스트셀러에서 키워드 수집
    """
    try:
        logger.info("11번가에서 키워드 수집 중...")
        
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        }
        
        try:
            response = requests.get(ELEVENST_TREND_URL, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 상품명 추출
                product_selectors = [
                    '.title',
                    '.product_name',
                    '[class*="product"] [class*="name"]',
                    '[class*="item"] [class*="title"]',
                    'a[href*="/prd/"]',
                ]
                
                product_names = []
                for selector in product_selectors:
                    elements = soup.select(selector)
                    for elem in elements[:max(100, max_keywords * 3)]:
                        text = elem.get_text(strip=True)
                        if text and len(text) > 2:
                            product_names.append(text)
                    if product_names:
                        break
                
                if product_names:
                    keywords = _extract_keywords_from_texts(product_names, max_keywords * 3)
                    return keywords
        except Exception as e:
            logger.debug(f"11번가 페이지 접근 실패: {e}")
        
        return []
    except Exception as e:
        logger.debug(f"11번가에서 키워드 수집 실패: {e}")
        return []

def _get_keywords_from_google_trends(driver: Optional[WebDriver], max_keywords: int) -> List[str]:
    """
    구글 트렌드에서 인기 키워드 수집
    """
    try:
        logger.info("구글 트렌드에서 키워드 수집 중...")
        
        if not driver:
            return []
        
        driver.get(GOOGLE_TRENDS_URL)
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(WAIT_TIMES['page_load'] * 2)
        
        # 트렌드 키워드 추출
        keyword_selectors = [
            ".trending-story-title",
            ".trending-story",
            "[class*='trending']",
            "[class*='keyword']",
            ".title",
        ]
        
        keywords = []
        for selector in keyword_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements[:max_keywords]:
                    text = elem.text.strip()
                    if text and 2 <= len(text) <= 50:
                        # 한글 키워드만 추출
                        if re.match(r'^[가-힣\s]+$', text):
                            keywords.append(text)
                if keywords:
                    break
            except:
                continue
        
        if keywords:
            return keywords[:max_keywords]
        
        return []
    except Exception as e:
        logger.debug(f"구글 트렌드에서 키워드 수집 실패: {e}")
        return []

