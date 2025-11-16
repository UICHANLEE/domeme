"""
유틸리티 함수 모듈
"""
import re
from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from logger import default_logger as logger

def extract_price_number(price_text: str) -> Optional[int]:
    """
    가격 텍스트에서 숫자만 추출
    
    Args:
        price_text: 가격 텍스트 (예: "29,530원", "12,000원")
    
    Returns:
        가격 숫자 (int), 파싱 실패시 None
    """
    if not price_text:
        return None
    
    # 콤마, 원, 공백 제거 후 숫자만 추출
    cleaned = price_text.replace(',', '').replace('원', '').replace(' ', '').strip()
    
    # 숫자만 추출 (정규식 사용)
    numbers = re.findall(r'\d+', cleaned)
    if numbers:
        try:
            return int(''.join(numbers))
        except ValueError:
            return None
    return None

def find_element_by_selectors(
    driver: WebDriver,
    selectors: list,
    parent: Optional[WebElement] = None
) -> Optional[WebElement]:
    """
    여러 선택자 중 하나로 요소 찾기
    
    Args:
        driver: WebDriver 객체
        selectors: CSS 선택자 리스트
        parent: 부모 요소 (None이면 driver에서 검색)
    
    Returns:
        찾은 요소 또는 None
    """
    search_context = parent if parent else driver
    
    for selector in selectors:
        try:
            element = search_context.find_element(By.CSS_SELECTOR, selector)
            logger.debug(f"요소 찾음: {selector}")
            return element
        except NoSuchElementException:
            continue
    
    return None

def safe_click(driver: WebDriver, element: WebElement) -> bool:
    """
    요소 클릭 시도 (여러 방법 시도)
    
    Args:
        driver: WebDriver 객체
        element: 클릭할 요소
    
    Returns:
        클릭 성공 여부
    """
    # 방법 1: 직접 클릭
    try:
        element.click()
        return True
    except Exception as e:
        logger.debug(f"직접 클릭 실패: {e}")
    
    # 방법 2: JavaScript로 클릭
    try:
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception as e:
        logger.debug(f"JavaScript 클릭 실패: {e}")
    
    # 방법 3: onclick 함수 직접 실행
    try:
        onclick_attr = element.get_attribute('onclick')
        if onclick_attr:
            driver.execute_script(onclick_attr)
            return True
    except Exception as e:
        logger.debug(f"onclick 함수 실행 실패: {e}")
    
    return False

def scroll_to_element(driver: WebDriver, element: WebElement) -> None:
    """요소가 보이도록 스크롤"""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    except Exception as e:
        logger.debug(f"스크롤 실패: {e}")

