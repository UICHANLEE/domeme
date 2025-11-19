"""
네이버 쇼핑 상품 검색 모듈
shopping.naver.com에서 상품 검색 및 정보 수집
"""
from typing import Optional, List, Dict
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import quote
import time
import re

from config import WAIT_TIMES, DEFAULT_TIMEOUT, USER_AGENT
from logger import default_logger as logger

# 네이버 쇼핑 URL
NAVER_SHOPPING_URL = "https://shopping.naver.com"
NAVER_SHOPPING_SEARCH_URL = "https://search.shopping.naver.com/search/all?query={keyword}"

# CSS 선택자 (실제 사이트 구조 확인 완료)
NAVER_SHOPPING_SELECTORS = {
    'search': {
        'search_input': [
            "input[name='query']",
            "input[placeholder*='검색']",
            "#_searchInput",
            ".search_input",
        ],
        'search_button': [
            "button[type='submit']",
            ".search_btn",
            "button.btn-search",
        ],
    },
    'product': {
        'list_container': [
            "div.basicList_list_basis__XVx_G",
            "div[class*='basicList']",
            "ul[class*='product']",
            "[class*='product-list']",
        ],
        'product_item': [
            "div.product_item__KQayS",
            "div[class*='product_item']",
            "div.basicList_item__eY7J4",
            "[class*='item']",
        ],
        'product_name': [
            "a.thumbnail_thumb__MG0r2.linkAnchor",
            "a[class*='link']",
            "a[class*='name']",
            "a[class*='title']",
            "[class*='name']",
        ],
        'product_price': [
            "span.product_num__WuH26",
            "span.adProduct_num__2Sl5g",
            "[class*='price']",
            "[class*='num']",
            "strong",
        ],
        'product_link': [
            "a.thumbnail_thumb__MG0r2.linkAnchor",
            "a[href*='/products/']",
            "a[href*='shopping']",
        ],
        'product_image': [
            "img[src*='shopping-phinf']",
            "img[src*='pstatic']",
            "img",
        ],
        'product_seller': [
            "[class*='mall']",
            "[class*='seller']",
            ".mall_name",
        ],
    },
}

def search_naver_shopping_products(
    driver: WebDriver,
    keyword: str,
    max_results: Optional[int] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None
) -> List[Dict]:
    """
    네이버 쇼핑에서 상품 검색
    
    Args:
        driver: WebDriver 객체
        keyword: 검색어
        max_results: 최대 결과 수
        min_price: 최소 가격 필터
        max_price: 최대 가격 필터
    
    Returns:
        상품 정보 리스트
    """
    try:
        logger.info(f"네이버 쇼핑에서 '{keyword}' 검색 중...")
        
        # 검색 URL 생성
        encoded_keyword = quote(keyword, safe='')
        search_url = NAVER_SHOPPING_SEARCH_URL.format(keyword=encoded_keyword)
        
        driver.get(search_url)
        
        # 페이지 로딩 대기
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(WAIT_TIMES['page_load'] * 2)
        
        # 스크롤하여 동적 콘텐츠 로드
        _scroll_page(driver)
        time.sleep(WAIT_TIMES['page_load'])
        
        products = []
        
        # 상품 목록 찾기
        product_items = []
        for selector in NAVER_SHOPPING_SELECTORS['product']['product_item']:
            try:
                product_items = driver.find_elements(By.CSS_SELECTOR, selector)
                if product_items:
                    logger.info(f"네이버 쇼핑에서 {len(product_items)}개 상품 요소 발견")
                    break
            except:
                continue
        
        if not product_items:
            logger.warning("네이버 쇼핑 상품 목록을 찾을 수 없습니다. 페이지 구조를 확인하세요.")
            return products
        
        # 각 상품 정보 추출
        for idx, item in enumerate(product_items[:max_results] if max_results else product_items):
            try:
                product_info = {}
                product_info['source'] = 'naver_shopping'
                product_info['search_keyword'] = keyword
                
                # 상품명 추출 (title 속성 우선, 없으면 textContent)
                name_elem = None
                for selector in NAVER_SHOPPING_SELECTORS['product']['product_name']:
                    try:
                        name_elem = item.find_element(By.CSS_SELECTOR, selector)
                        if name_elem:
                            break
                    except:
                        continue
                
                if name_elem:
                    # title 속성에서 상품명 추출 시도
                    name = name_elem.get_attribute('title') or name_elem.text.strip()
                    product_info['name'] = name
                else:
                    product_info['name'] = ''
                
                # 가격 추출
                price_elem = None
                for selector in NAVER_SHOPPING_SELECTORS['product']['product_price']:
                    try:
                        price_elem = item.find_element(By.CSS_SELECTOR, selector)
                        if price_elem:
                            break
                    except:
                        continue
                
                if price_elem:
                    price_text = price_elem.text.strip()
                    product_info['price'] = price_text
                    # 숫자만 추출하여 price_value 생성
                    price_value = _extract_price_value(price_text)
                    product_info['price_value'] = price_value
                else:
                    product_info['price'] = ''
                    product_info['price_value'] = 0
                
                # 가격 필터링
                if min_price and product_info.get('price_value', 0) < min_price:
                    continue
                if max_price and product_info.get('price_value', 0) > max_price:
                    continue
                
                # 링크 추출
                link_elem = None
                for selector in NAVER_SHOPPING_SELECTORS['product']['product_link']:
                    try:
                        link_elem = item.find_element(By.CSS_SELECTOR, selector)
                        if link_elem:
                            break
                    except:
                        continue
                
                if link_elem:
                    href = link_elem.get_attribute('href')
                    if href and not href.startswith('http'):
                        href = NAVER_SHOPPING_URL + href
                    product_info['link'] = href or ''
                else:
                    product_info['link'] = ''
                
                # 이미지 추출
                image_elem = None
                for selector in NAVER_SHOPPING_SELECTORS['product']['product_image']:
                    try:
                        image_elem = item.find_element(By.CSS_SELECTOR, selector)
                        if image_elem:
                            break
                    except:
                        continue
                
                if image_elem:
                    product_info['image'] = image_elem.get_attribute('src') or image_elem.get_attribute('data-src') or ''
                else:
                    product_info['image'] = ''
                
                # 판매자 추출
                seller_elem = None
                for selector in NAVER_SHOPPING_SELECTORS['product']['product_seller']:
                    try:
                        seller_elem = item.find_element(By.CSS_SELECTOR, selector)
                        if seller_elem:
                            break
                    except:
                        continue
                
                product_info['seller'] = seller_elem.text.strip() if seller_elem else ''
                
                # 평점 추출
                rating_elem = None
                for selector in NAVER_SHOPPING_SELECTORS['product']['product_rating']:
                    try:
                        rating_elem = item.find_element(By.CSS_SELECTOR, selector)
                        if rating_elem:
                            break
                    except:
                        continue
                
                product_info['rating'] = rating_elem.text.strip() if rating_elem else ''
                
                # 리뷰 수 추출
                review_elem = None
                for selector in NAVER_SHOPPING_SELECTORS['product']['product_review_count']:
                    try:
                        review_elem = item.find_element(By.CSS_SELECTOR, selector)
                        if review_elem:
                            break
                    except:
                        continue
                
                product_info['review_count'] = review_elem.text.strip() if review_elem else ''
                
                # 상품 ID 추출 (링크에서)
                if product_info.get('link'):
                    product_id_match = re.search(r'/products/(\d+)', product_info['link'])
                    if product_id_match:
                        product_info['product_id'] = product_id_match.group(1)
                    else:
                        product_info['product_id'] = ''
                else:
                    product_info['product_id'] = ''
                
                if product_info.get('name'):
                    products.append(product_info)
                    
            except Exception as e:
                logger.debug(f"네이버 쇼핑 상품 {idx+1} 파싱 실패: {e}")
                continue
        
        logger.info(f"네이버 쇼핑에서 {len(products)}개 상품 정보를 추출했습니다.")
        return products
        
    except Exception as e:
        logger.error(f"네이버 쇼핑 상품 검색 실패: {e}", exc_info=True)
        return []

def _extract_price_value(price_text: str) -> int:
    """가격 텍스트에서 숫자만 추출"""
    try:
        # 콤마와 원 제거 후 숫자만 추출
        cleaned = re.sub(r'[^\d]', '', price_text)
        return int(cleaned) if cleaned else 0
    except:
        return 0

def _scroll_page(driver: WebDriver, scroll_count: int = 3):
    """페이지 스크롤하여 동적 콘텐츠 로드"""
    try:
        for i in range(scroll_count):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(WAIT_TIMES['scroll'])
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(WAIT_TIMES['scroll'])
    except:
        pass

