"""
쿠팡 쇼핑몰 상품 검색 모듈
www.coupang.com에서 상품 검색 및 정보 수집
undetected-chromedriver를 사용하여 봇 차단 우회
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

# undetected-chromedriver 임포트 (쿠팡 봇 차단 우회용)
try:
    import undetected_chromedriver as uc
    UC_AVAILABLE = True
except ImportError:
    UC_AVAILABLE = False
    logger.warning("undetected-chromedriver가 설치되지 않았습니다. 'pip install undetected-chromedriver' 실행 필요")

# 쿠팡 쇼핑몰 URL
COUPANG_URL = "https://www.coupang.com"
COUPANG_SEARCH_URL = "https://www.coupang.com/np/search?q={keyword}"

# CSS 선택자 (쿠팡 쇼핑몰 구조 - 일반적인 패턴 사용)
COUPANG_SELECTORS = {
    'search': {
        'search_input': [
            "input[name='q']",
            "input[placeholder*='검색']",
            "#headerSearchKeyword",
            ".header-search-input",
            "input[type='search']",
        ],
        'search_button': [
            "button[type='submit']",
            ".header-search-button",
            "button.btn-search",
            "button[aria-label*='검색']",
        ],
    },
    'product': {
        'list_container': [
            "ul.search-product-list",
            "#productList",
            ".search-product-list",
            "[class*='product-list']",
            "ul[class*='search']",
        ],
        'product_item': [
            "li.search-product",
            "li[class*='search-product']",
            ".search-product",
            "[data-product-id]",
            "li[class*='product']",
        ],
        'product_name': [
            "a.search-product-link",
            ".name",
            ".product-name",
            "a.name",
            "[class*='name']",
            "dd.name",
        ],
        'product_price': [
            "strong.price-value",
            ".price-value",
            ".price",
            "[class*='price-value']",
            "[class*='price']",
            "strong",
        ],
        'product_link': [
            "a.search-product-link",
            "a[href*='/products/']",
            "a[href*='/np/products']",
            ".product-link",
        ],
        'product_image': [
            "img.search-product-wrap-img",
            "img[src*='coupang']",
            "img.product-image",
            "dt img",
        ],
        'product_rating': [
            ".rating",
            ".star-rating",
            "[class*='rating']",
            "[class*='star']",
        ],
        'product_review_count': [
            ".rating-total-count",
            ".review-count",
            "[class*='review']",
            "[class*='count']",
        ],
    },
}

def get_coupang_driver(headless: bool = False) -> WebDriver:
    """
    쿠팡 전용 WebDriver 생성 (undetected-chromedriver 사용)
    
    Args:
        headless: 헤드리스 모드 사용 여부
    
    Returns:
        WebDriver 객체
    """
    if not UC_AVAILABLE:
        raise ImportError("undetected-chromedriver가 필요합니다. 'pip install undetected-chromedriver' 실행하세요.")
    
    try:
        logger.info("쿠팡 전용 드라이버 생성 중 (undetected-chromedriver 사용)...")
        
        options = uc.ChromeOptions()
        
        if headless:
            options.add_argument('--headless=new')  # 새로운 headless 모드
        
        # 봇 탐지 우회 옵션
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-web-security')
        options.add_argument('--lang=ko-KR')
        options.add_argument('--accept-lang=ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7')
        
        # User-Agent 설정
        options.add_argument(f'user-agent={USER_AGENT}')
        
        # undetected-chromedriver로 드라이버 생성
        driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)
        
        # 추가 스크립트로 봇 탐지 우회
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ko-KR', 'ko', 'en-US', 'en']
                });
            '''
        })
        
        logger.info("✓ 쿠팡 전용 드라이버 생성 완료")
        return driver
        
    except Exception as e:
        logger.error(f"쿠팡 드라이버 생성 실패: {e}")
        raise

def search_coupang_products(
    driver: Optional[WebDriver] = None,
    keyword: str = "",
    max_results: Optional[int] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    headless: bool = False
) -> List[Dict]:
    """
    쿠팡 쇼핑몰에서 상품 검색 (undetected-chromedriver 사용)
    
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
        logger.info(f"🚀 쿠팡 쇼핑몰에서 '{keyword}' 검색 중 (고급 봇 우회 기술 사용)...")
        
        # 드라이버가 없으면 쿠팡 전용 드라이버 생성
        if driver is None:
            driver = get_coupang_driver(headless=headless)
            should_close_driver = True
        
        # 검색 URL 생성
        encoded_keyword = quote(keyword, safe='')
        search_url = COUPANG_SEARCH_URL.format(keyword=encoded_keyword)
        
        logger.info(f"쿠팡 검색 URL: {search_url}")
        
        try:
            driver.get(search_url)
            
            # 페이지 로딩 대기 (쿠팡은 더 긴 대기 시간 필요)
            WebDriverWait(driver, DEFAULT_TIMEOUT * 3).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 추가 대기 (쿠팡은 동적 로딩이 많음)
            time.sleep(WAIT_TIMES['page_load'] * 4)
            
            # 현재 URL 확인
            current_url = driver.current_url
            logger.info(f"현재 페이지 URL: {current_url}")
            
            # 에러 페이지인지 확인
            if 'error' in current_url.lower() or 'chrome-error' in current_url.lower():
                raise Exception(f"에러 페이지로 이동됨: {current_url}")
            
            # 페이지 제목 확인
            try:
                page_title = driver.title
                logger.info(f"페이지 제목: {page_title}")
                if not page_title or len(page_title) < 3:
                    logger.warning("페이지 제목이 비어있습니다. 페이지가 제대로 로드되지 않았을 수 있습니다.")
            except:
                pass
            
            logger.info("✓ 쿠팡 페이지 접근 성공!")
            
        except Exception as e:
            logger.error(f"쿠팡 접근 실패: {e}")
            if should_close_driver and driver:
                try:
                    driver.quit()
                except:
                    pass
            return []
        
        # 스크롤하여 동적 콘텐츠 로드
        _scroll_page(driver)
        time.sleep(WAIT_TIMES['page_load'])
        
        products = []
        
        # 상품 목록 찾기 (여러 방법 시도)
        product_items = []
        
        # 추가 대기 (쿠팡은 동적 로딩이 많음)
        time.sleep(WAIT_TIMES['page_load'] * 2)
        
        # 방법 1: 직접 상품 아이템 찾기
        for selector in COUPANG_SELECTORS['product']['product_item']:
            try:
                product_items = driver.find_elements(By.CSS_SELECTOR, selector)
                if product_items:
                    logger.info(f"쿠팡에서 {len(product_items)}개 상품 요소 발견 (선택자: {selector})")
                    break
            except:
                continue
        
        # 방법 2: 컨테이너를 먼저 찾고 그 안에서 상품 찾기
        if not product_items:
            for container_selector in COUPANG_SELECTORS['product']['list_container']:
                try:
                    container = driver.find_element(By.CSS_SELECTOR, container_selector)
                    if container:
                        # 컨테이너 내에서 상품 찾기
                        for item_selector in COUPANG_SELECTORS['product']['product_item']:
                            try:
                                product_items = container.find_elements(By.CSS_SELECTOR, item_selector)
                                if product_items:
                                    logger.info(f"쿠팡에서 {len(product_items)}개 상품 요소 발견 (컨테이너: {container_selector})")
                                    break
                            except:
                                continue
                        if product_items:
                            break
                except:
                    continue
        
        # 방법 3: 일반적인 패턴으로 찾기
        if not product_items:
            try:
                # data-product-id 속성이 있는 요소 찾기
                product_items = driver.find_elements(By.CSS_SELECTOR, "[data-product-id]")
                if product_items:
                    logger.info(f"쿠팡에서 {len(product_items)}개 상품 요소 발견 (data-product-id)")
            except:
                pass
        
        # 방법 4: 쿠팡 실제 구조 확인 (ul.search-product-wrap, li.search-product 등)
        if not product_items:
            try:
                # 쿠팡의 실제 구조 시도
                alternative_selectors = [
                    "ul.search-product-list li",
                    "ul.search-product-wrap li",
                    "div.search-product-list li",
                    "li[class*='search-product']",
                    "div[class*='search-product']",
                    "ul[class*='product'] li",
                    "li[data-product-id]",
                    "a[href*='/products/']",
                ]
                for selector in alternative_selectors:
                    try:
                        product_items = driver.find_elements(By.CSS_SELECTOR, selector)
                        if product_items and len(product_items) > 0:
                            logger.info(f"쿠팡에서 {len(product_items)}개 상품 요소 발견 (대체 선택자: {selector})")
                            break
                    except:
                        continue
            except:
                pass
        
        if not product_items:
            logger.warning("쿠팡 상품 목록을 찾을 수 없습니다. 페이지 구조를 확인하세요.")
            # 디버깅을 위해 페이지 소스 일부 출력
            try:
                # 페이지에서 상품 관련 요소 찾기 시도
                all_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/products/']")
                logger.info(f"상품 링크 발견: {len(all_links)}개")
                
                if all_links:
                    # 링크의 부모 요소를 상품 아이템으로 사용
                    seen_parents = set()
                    for link in all_links[:20]:  # 최대 20개만 확인
                        try:
                            parent = link.find_element(By.XPATH, "./ancestor::li[1]")
                            parent_id = id(parent)
                            if parent_id not in seen_parents:
                                product_items.append(parent)
                                seen_parents.add(parent_id)
                        except:
                            try:
                                parent = link.find_element(By.XPATH, "./ancestor::div[contains(@class, 'product') or contains(@class, 'item')][1]")
                                parent_id = id(parent)
                                if parent_id not in seen_parents:
                                    product_items.append(parent)
                                    seen_parents.add(parent_id)
                            except:
                                continue
                    
                    if product_items:
                        logger.info(f"링크 부모 요소로 {len(product_items)}개 상품 요소 발견")
            except Exception as e:
                logger.debug(f"디버깅 중 오류: {e}")
            
            if not product_items:
                # 페이지 소스 일부 출력
                try:
                    page_source = driver.page_source[:2000]
                    logger.debug(f"페이지 소스 일부: {page_source}")
                except:
                    pass
                return products
        
        # 각 상품 정보 추출
        for idx, item in enumerate(product_items[:max_results] if max_results else product_items):
            try:
                product_info = {}
                product_info['source'] = 'coupang'
                product_info['search_keyword'] = keyword
                
                # 상품명 추출 (여러 방법 시도)
                name_elem = None
                for selector in COUPANG_SELECTORS['product']['product_name']:
                    try:
                        name_elem = item.find_element(By.CSS_SELECTOR, selector)
                        if name_elem and name_elem.text.strip():
                            break
                    except:
                        continue
                
                # 상품명이 없으면 링크에서 추출 시도
                if not name_elem or not name_elem.text.strip():
                    try:
                        # 상품 링크 찾기
                        link_elem = item.find_element(By.CSS_SELECTOR, "a[href*='/products/']")
                        if link_elem:
                            # 링크의 title 속성 또는 텍스트 사용
                            name_text = link_elem.get_attribute('title') or link_elem.text.strip()
                            if name_text:
                                product_info['name'] = name_text
                            else:
                                name_elem = link_elem
                        else:
                            # 일반 링크 찾기
                            link_elem = item.find_element(By.CSS_SELECTOR, "a")
                            if link_elem:
                                name_elem = link_elem
                    except:
                        pass
                
                if not product_info.get('name'):
                    product_info['name'] = name_elem.text.strip() if name_elem else ''
                
                # 가격 추출
                price_elem = None
                for selector in COUPANG_SELECTORS['product']['product_price']:
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
                for selector in COUPANG_SELECTORS['product']['product_link']:
                    try:
                        link_elem = item.find_element(By.CSS_SELECTOR, selector)
                        if link_elem:
                            break
                    except:
                        continue
                
                if link_elem:
                    href = link_elem.get_attribute('href')
                    if href and not href.startswith('http'):
                        href = COUPANG_URL + href
                    product_info['link'] = href or ''
                else:
                    product_info['link'] = ''
                
                # 이미지 추출
                image_elem = None
                for selector in COUPANG_SELECTORS['product']['product_image']:
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
                
                # 평점 추출
                rating_elem = None
                for selector in COUPANG_SELECTORS['product']['product_rating']:
                    try:
                        rating_elem = item.find_element(By.CSS_SELECTOR, selector)
                        if rating_elem:
                            break
                    except:
                        continue
                
                product_info['rating'] = rating_elem.text.strip() if rating_elem else ''
                
                # 리뷰 수 추출
                review_elem = None
                for selector in COUPANG_SELECTORS['product']['product_review_count']:
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
                logger.debug(f"쿠팡 상품 {idx+1} 파싱 실패: {e}")
                continue
        
        logger.info(f"✓ 쿠팡에서 {len(products)}개 상품 정보를 추출했습니다.")
        return products
        
    except Exception as e:
        logger.error(f"쿠팡 상품 검색 실패: {e}", exc_info=True)
        return []
    finally:
        # 자동 생성한 드라이버는 닫지 않음 (재사용 가능)
        # 필요시 호출자가 닫아야 함
        # 드라이버 종료는 main.py에서 처리
        pass

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

