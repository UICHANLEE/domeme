"""
11번가(11st) 상품 검색 모듈
www.11st.co.kr에서 상품 검색 및 정보 수집
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
from scraper import get_chrome_driver

# 11번가 URL
ST11_URL = "https://www.11st.co.kr"
ST11_SEARCH_URL = "https://search.11st.co.kr/Search.tmall?kwd={keyword}"

def search_11st_products(
    driver: Optional[WebDriver] = None,
    keyword: str = "",
    max_results: Optional[int] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    headless: bool = False
) -> List[Dict]:
    """
    11번가에서 상품 검색
    
    Args:
        driver: WebDriver 객체 (None이면 자동 생성)
        keyword: 검색어
        max_results: 최대 결과 수
        min_price: 최소 가격 필터
        max_price: 최대 가격 필터
        headless: 헤드리스 모드 사용 여부
    
    Returns:
        상품 정보 리스트
    """
    should_close_driver = False
    
    try:
        logger.info(f"11번가에서 '{keyword}' 검색 중...")
        
        # 드라이버가 없으면 생성
        if driver is None:
            driver = get_chrome_driver(headless=headless)
            should_close_driver = True
        
        # 검색 URL 생성
        encoded_keyword = quote(keyword, safe='')
        search_url = ST11_SEARCH_URL.format(keyword=encoded_keyword)
        
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
        selectors = [
            "div.c_card_item",
            "div[class*='card']",
            "li[class*='item']",
            "div[class*='product']",
        ]
        
        for selector in selectors:
            try:
                product_items = driver.find_elements(By.CSS_SELECTOR, selector)
                if product_items:
                    logger.info(f"11번가에서 {len(product_items)}개 상품 요소 발견")
                    break
            except:
                continue
        
        if not product_items:
            logger.warning("11번가 상품 목록을 찾을 수 없습니다.")
            return products
        
        # 각 상품 정보 추출
        for idx, item in enumerate(product_items[:max_results] if max_results else product_items):
            try:
                product_info = {}
                product_info['source'] = '11st'
                product_info['search_keyword'] = keyword
                
                # 상품명 추출
                name_elem = None
                name_selectors = [
                    "a.c_card_link",
                    "a[class*='link']",
                    "p.c_card_info_title",
                    "[class*='title']",
                ]
                
                for selector in name_selectors:
                    try:
                        name_elem = item.find_element(By.CSS_SELECTOR, selector)
                        if name_elem and name_elem.text.strip():
                            break
                    except:
                        continue
                
                if name_elem:
                    product_info['name'] = name_elem.text.strip()
                else:
                    product_info['name'] = ''
                
                # 가격 추출
                price_elem = None
                price_selectors = [
                    "span.c_card_price",
                    "strong[class*='price']",
                    "[class*='price']",
                    "strong",
                ]
                
                for selector in price_selectors:
                    try:
                        price_elem = item.find_element(By.CSS_SELECTOR, selector)
                        if price_elem and price_elem.text.strip():
                            break
                    except:
                        continue
                
                if price_elem:
                    price_text = price_elem.text.strip()
                    product_info['price'] = price_text
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
                link_selectors = [
                    "a.c_card_link",
                    "a[href*='/products/']",
                    "a[class*='link']",
                ]
                
                for selector in link_selectors:
                    try:
                        link_elem = item.find_element(By.CSS_SELECTOR, selector)
                        if link_elem:
                            break
                    except:
                        continue
                
                if link_elem:
                    href = link_elem.get_attribute('href')
                    if href and not href.startswith('http'):
                        href = ST11_URL + href
                    product_info['link'] = href or ''
                else:
                    product_info['link'] = ''
                
                # 이미지 추출
                image_elem = None
                try:
                    image_elem = item.find_element(By.CSS_SELECTOR, "img")
                except:
                    pass
                
                if image_elem:
                    product_info['image'] = image_elem.get_attribute('src') or image_elem.get_attribute('data-src') or ''
                else:
                    product_info['image'] = ''
                
                # 판매자 추출
                seller_elem = None
                try:
                    seller_elem = item.find_element(By.CSS_SELECTOR, "[class*='seller']")
                except:
                    pass
                
                product_info['seller'] = seller_elem.text.strip() if seller_elem else ''
                
                # 상품 ID 추출
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
                logger.debug(f"11번가 상품 {idx+1} 파싱 실패: {e}")
                continue
        
        logger.info(f"11번가에서 {len(products)}개 상품 정보를 추출했습니다.")
        return products
        
    except Exception as e:
        logger.error(f"11번가 상품 검색 실패: {e}", exc_info=True)
        return []
    finally:
        if should_close_driver and driver:
            try:
                driver.quit()
            except:
                pass

def _extract_price_value(price_text: str) -> int:
    """가격 텍스트에서 숫자만 추출"""
    try:
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

