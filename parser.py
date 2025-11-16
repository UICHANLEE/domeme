"""
검색 결과 파싱 모듈
"""
import re
from typing import Optional, List, Dict
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from config import SELECTORS
from utils import extract_price_number, find_element_by_selectors
from logger import default_logger as logger

def parse_search_results(
    driver: WebDriver,
    max_results: Optional[int] = None,
    min_price: Optional[int] = None
) -> List[Dict]:
    """
    검색 결과 페이지에서 상품 정보 파싱
    
    Args:
        driver: Selenium WebDriver 객체
        max_results: 가져올 최대 결과 수
        min_price: 최소 가격 (이 가격 이상인 상품만 필터링)
    
    Returns:
        상품 정보 리스트
    """
    results = []
    
    try:
        # 상품 컨테이너 찾기
        products = _find_product_containers(driver)
        
        if not products:
            logger.warning("상품 요소를 찾지 못했습니다.")
            return results
        
        # 각 상품 정보 추출
        product_list = products[:max_results] if max_results else products
        for idx, product in enumerate(product_list):
            try:
                product_info = _parse_single_product(product, idx)
                
                # 가격 필터링 적용
                if min_price is not None:
                    if product_info.get('price_value') is None:
                        logger.debug(f"상품 {idx+1}: 가격을 파싱할 수 없어 건너뜀")
                        continue
                    if product_info['price_value'] < min_price:
                        logger.debug(
                            f"상품 {idx+1}: 가격 {product_info.get('price', 'N/A')}이(가) "
                            f"최소 가격 {min_price:,}원 미만이어서 건너뜀"
                        )
                        continue
                
                # 상품명이 있으면 결과에 추가
                if product_info.get('name'):
                    results.append(product_info)
                else:
                    logger.debug(f"상품 {idx+1}: 상품명을 찾을 수 없어 건너뜀")
                    
            except Exception as e:
                logger.error(f"상품 {idx+1} 파싱 중 오류: {e}", exc_info=True)
                continue
        
    except Exception as e:
        logger.error(f"결과 파싱 중 오류: {e}", exc_info=True)
    
    return results

def _find_product_containers(driver: WebDriver) -> List:
    """상품 컨테이너 요소 찾기"""
    products = []
    for selector in SELECTORS['product']['container']:
        try:
            products = driver.find_elements(By.CSS_SELECTOR, selector)
            if len(products) > 0:
                logger.info(f"상품 요소 찾음: {selector} ({len(products)}개)")
                break
        except:
            continue
    return products

def _parse_single_product(product, idx: int) -> Dict:
    """단일 상품 정보 파싱"""
    product_info = {}
    
    # 상품번호 추출
    product_id = _extract_product_id(product)
    product_info['product_id'] = product_id or ''
    
    # 상품명 추출
    product_info['name'] = _extract_product_name(product)
    
    # 가격 추출
    price_value, price_display = _extract_price(product, idx)
    product_info['price'] = price_display
    product_info['price_value'] = price_value
    
    # 이미지 추출
    product_info['image'] = _extract_image(product)
    
    # 판매자 정보 추출
    product_info['seller'] = _extract_seller(product)
    
    # 상품 상세 링크 생성
    if product_id:
        product_info['link'] = (
            f"https://domemedb.domeggook.com/index/item/itemView.php?itemNo={product_id}"
        )
    else:
        product_info['link'] = ''
    
    # 등급 추출
    product_info['grade'] = _extract_grade(product)
    
    # 빠른배송 여부
    product_info['fast_delivery'] = _check_fast_delivery(product)
    
    return product_info

def _extract_product_id(product) -> Optional[str]:
    """상품번호 추출"""
    # checkbox의 value 속성에서 상품번호 추출
    try:
        checkbox = product.find_element(By.CSS_SELECTOR, SELECTORS['product']['checkbox'])
        product_id = checkbox.get_attribute('value')
        if product_id:
            return product_id
    except:
        pass
    
    # span.txt8에서 상품번호 추출
    try:
        product_id_elems = product.find_elements(By.CSS_SELECTOR, "span.txt8")
        for elem in product_id_elems:
            text = elem.text.strip()
            if text.isdigit() and len(text) >= 6:
                return text
    except:
        pass
    
    return None

def _extract_product_name(product) -> str:
    """상품명 추출"""
    try:
        name_elem = product.find_element(By.CSS_SELECTOR, SELECTORS['product']['name'])
        return name_elem.text.strip()
    except:
        # 백업: main_cont_text1에서 추출
        try:
            name_elem = product.find_element(By.CSS_SELECTOR, ".main_cont_text1.b")
            return name_elem.text.strip()
        except:
            return ''

def _extract_price(product, idx: int) -> tuple:
    """가격 추출"""
    price_value = None
    price_display = ''
    
    # 다양한 선택자 시도
    for selector in SELECTORS['product']['price']:
        try:
            price_elem = product.find_element(By.CSS_SELECTOR, selector)
            price_text = price_elem.text.strip()
            
            if price_text:
                price_value = extract_price_number(price_text)
                if price_value is not None and price_value >= 100:
                    price_display = f"{price_value:,}원"
                    return price_value, price_display
        except:
            continue
    
    # 컨테이너에서 찾기
    try:
        price_container = product.find_element(By.CSS_SELECTOR, ".main_cont_text1.priceLg")
        try:
            price_elem = price_container.find_element(By.CSS_SELECTOR, "strong")
            price_text = price_elem.text.strip()
        except:
            price_text = price_container.text.strip()
        
        if price_text:
            price_value = extract_price_number(price_text)
            if price_value is not None and price_value >= 100:
                price_display = f"{price_value:,}원"
                return price_value, price_display
    except:
        pass
    
    # 모든 strong 태그에서 찾기
    try:
        strong_elems = product.find_elements(By.CSS_SELECTOR, "strong")
        for strong in strong_elems:
            text = strong.text.strip()
            if not text:
                continue
            temp_value = extract_price_number(text)
            if temp_value is not None and 100 <= temp_value <= 10000000:
                price_value = temp_value
                price_display = f"{price_value:,}원"
                return price_value, price_display
    except:
        pass
    
    return None, ''

def _extract_image(product) -> str:
    """이미지 URL 추출"""
    try:
        img_elem = product.find_element(By.CSS_SELECTOR, SELECTORS['product']['image'])
        return img_elem.get_attribute('src') or img_elem.get_attribute('data-src') or ''
    except:
        # 백업: 모든 img 태그에서 상품 이미지 찾기
        try:
            imgs = product.find_elements(By.CSS_SELECTOR, "img")
            for img in imgs:
                src = img.get_attribute('src') or ''
                if 'domeggook.com' in src and 'upload/item' in src:
                    return src
        except:
            pass
        return ''

def _extract_seller(product) -> str:
    """판매자 정보 추출"""
    try:
        seller_elem = product.find_element(By.CSS_SELECTOR, SELECTORS['product']['seller'])
        return seller_elem.text.strip()
    except:
        return ''

def _extract_grade(product) -> str:
    """등급 추출"""
    try:
        grade_elems = product.find_elements(By.CSS_SELECTOR, ".main_cont_text3")
        for elem in grade_elems:
            text = elem.text.strip()
            if '등급' in text:
                try:
                    strong = elem.find_element(By.CSS_SELECTOR, "strong")
                    return strong.text.strip()
                except:
                    match = re.search(r'(\d+)등급', text)
                    if match:
                        return match.group(1)
    except:
        pass
    return ''

def _check_fast_delivery(product) -> bool:
    """빠른배송 여부 확인"""
    try:
        product.find_element(By.CSS_SELECTOR, ".main_cont_bu9")
        return True
    except:
        return False

