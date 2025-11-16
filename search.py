"""
상품 검색 모듈
"""
from typing import Optional, Tuple, List, Dict, Union
from urllib.parse import quote
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time

from config import (
    BASE_URL, SEARCH_URL_TEMPLATE, SELECTORS, WAIT_TIMES,
    DEFAULT_TIMEOUT, PAGE_LOAD_TIMEOUT
)
from scraper import get_chrome_driver
from login import login_to_domeggook
from parser import parse_search_results
from logger import default_logger as logger

def search_products(
    search_keyword: str,
    headless: bool = True,
    max_results: Optional[int] = None,
    use_direct_url: bool = False,
    min_price: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    return_driver: bool = False,
    driver: Optional[WebDriver] = None
) -> List[Dict] | Tuple[List[Dict], WebDriver]:
    """
    도매꾹 사이트에서 상품 검색
    
    Args:
        search_keyword: 검색할 키워드
        headless: 헤드리스 모드 사용 여부
        max_results: 가져올 최대 결과 수 (None이면 모두 가져옴)
        use_direct_url: True면 검색 폼 대신 직접 URL로 접근
        min_price: 최소 가격 (이 가격 이상인 상품만 필터링)
        username: 로그인 아이디
        password: 비밀번호
        return_driver: True면 driver도 함께 반환
        driver: 기존 driver 재사용 (None이면 새로 생성)
    
    Returns:
        검색 결과 리스트 또는 (결과 리스트, driver) 튜플
    """
    if driver is None:
        driver = get_chrome_driver(headless=headless)
        needs_login = True
    else:
        needs_login = False
    
    try:
        # 로그인 (필요한 경우)
        if needs_login:
            if not login_to_domeggook(driver, username=username, password=password):
                logger.error("로그인 실패로 검색을 중단합니다.")
                if return_driver:
                    return [], driver
                driver.quit()
                return []
        
        # 직접 URL 접근 방식
        if use_direct_url:
            return _search_with_direct_url(
                driver, search_keyword, max_results, min_price, return_driver
            )
        else:
            return _search_with_form(
                driver, search_keyword, max_results, min_price, return_driver
            )
            
    except Exception as e:
        logger.error(f"검색 실패: {e}", exc_info=True)
        if return_driver:
            return [], driver if driver else None
        if driver and not return_driver:
            driver.quit()
        return []

def _search_with_direct_url(
    driver: WebDriver,
    search_keyword: str,
    max_results: Optional[int],
    min_price: Optional[int],
    return_driver: bool
) -> Union[List[Dict], Tuple[List[Dict], WebDriver], Tuple[List[Dict], None]]:
    """직접 URL 접근 방식으로 검색"""
    try:
        logger.info(f"검색어 '{search_keyword}'로 직접 URL 접근...")
        encoded_keyword = quote(search_keyword, safe='')
        search_url = SEARCH_URL_TEMPLATE.format(keyword=encoded_keyword)
        
        driver.get(search_url)
        logger.info(f"검색 URL로 직접 접근: {search_url}")
        
        # 페이지 로딩 대기
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # 검색 결과 요소 로드 대기
        _wait_for_search_results(driver)
        
        # 페이지 스크롤하여 동적 콘텐츠 로드
        _scroll_page(driver)
        time.sleep(WAIT_TIMES['page_load'])
        
        # 검색 결과 파싱
        results = parse_search_results(driver, max_results, min_price=min_price)
        _log_search_complete(results, min_price)
        
        if return_driver:
            return results, driver
        return results
        
    except Exception as e:
        logger.error(f"직접 URL 접근 실패: {e}", exc_info=True)
        if return_driver:
            return [], driver
        return []

def _search_with_form(
    driver: WebDriver,
    search_keyword: str,
    max_results: Optional[int],
    min_price: Optional[int],
    return_driver: bool
) -> Union[List[Dict], Tuple[List[Dict], WebDriver], Tuple[List[Dict], None]]:
    """검색 폼 사용 방식으로 검색"""
    try:
        logger.info(f"검색어 '{search_keyword}'로 검색 시작...")
        
        # 메인 페이지로 이동
        driver.get(BASE_URL)
        
        # 페이지 로딩 대기
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(WAIT_TIMES['page_load'])
        
        # 검색창 찾기
        search_input = _find_search_input(driver)
        if not search_input:
            raise Exception("검색창을 찾을 수 없습니다.")
        
        # 검색어 입력
        search_input.clear()
        search_input.send_keys(search_keyword)
        time.sleep(WAIT_TIMES['element'])
        
        # 검색 실행
        _execute_search(driver, search_input)
        
        # 검색 결과 페이지 로딩 대기
        _wait_for_search_results_page(driver)
        
        # 검색 결과 요소 로드 대기
        _wait_for_search_results(driver)
        
        # 페이지 스크롤하여 동적 콘텐츠 로드
        _scroll_page(driver)
        time.sleep(WAIT_TIMES['page_load'])
        
        # 검색 결과 파싱
        results = parse_search_results(driver, max_results, min_price=min_price)
        _log_search_complete(results, min_price)
        
        if return_driver:
            return results, driver
        return results
        
    except Exception as e:
        logger.error(f"검색 실패: {e}", exc_info=True)
        if return_driver:
            return [], driver
        return []

def _find_search_input(driver: WebDriver):
    """검색창 찾기"""
    from utils import find_element_by_selectors
    
    # CSS 선택자로 찾기
    search_input = find_element_by_selectors(driver, SELECTORS['search']['search_input'])
    if search_input:
        return search_input
    
    # name 속성으로 직접 찾기
    try:
        return driver.find_element(By.NAME, "sw")
    except NoSuchElementException:
        pass
    
    # 모든 input 요소 확인
    inputs = driver.find_elements(By.TAG_NAME, "input")
    for inp in inputs:
        inp_name = inp.get_attribute("name") or ""
        inp_type = inp.get_attribute("type")
        inp_title = inp.get_attribute("title") or ""
        if inp_name == "sw" or (inp_type == "text" and "검색" in inp_title):
            return inp
    
    return None

def _execute_search(driver: WebDriver, search_input) -> None:
    """검색 실행"""
    from utils import find_element_by_selectors
    
    search_button = find_element_by_selectors(driver, SELECTORS['search']['search_button'])
    
    if search_button:
        search_button.click()
        logger.info("검색 버튼 클릭")
    else:
        search_input.send_keys(Keys.RETURN)
        logger.info("Enter 키로 검색 실행")

def _wait_for_search_results_page(driver: WebDriver) -> None:
    """검색 결과 페이지 로딩 대기"""
    initial_url = driver.current_url
    
    try:
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            lambda d: (
                "supplyList.php" in d.current_url or
                "search" in d.current_url.lower() or
                d.current_url != initial_url
            )
        )
        logger.info(f"검색 결과 페이지로 이동: {driver.current_url}")
    except TimeoutException:
        logger.warning("URL 변경이 감지되지 않았지만 계속 진행합니다...")

def _wait_for_search_results(driver: WebDriver) -> None:
    """검색 결과 요소 로드 대기"""
    selectors = [
        ".sub_cont_bane1",
        ".sub_cont_bane1_SetListGallery",
        "[class*='item']"
    ]
    
    for selector in selectors:
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            logger.info(f"검색 결과 요소 로드 완료: {selector}")
            return
        except TimeoutException:
            continue
    
    logger.warning("검색 결과 요소를 찾지 못했지만 계속 진행합니다...")

def _scroll_page(driver: WebDriver) -> None:
    """페이지 스크롤하여 동적 콘텐츠 로드"""
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(WAIT_TIMES['scroll'])
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(WAIT_TIMES['scroll'])
    except:
        pass

def _log_search_complete(results: List[Dict], min_price: Optional[int]) -> None:
    """검색 완료 로그 출력"""
    if min_price:
        logger.info(f"검색 완료! {min_price:,}원 이상 상품 {len(results)}개 발견")
    else:
        logger.info(f"검색 완료! 총 {len(results)}개 결과 발견")

