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
    BASE_URL, SEARCH_URL_TEMPLATE, SEARCH_URL_TEMPLATE_WITH_PAGE, SELECTORS, WAIT_TIMES,
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
    driver: Optional[WebDriver] = None,
    max_pages: Optional[int] = None
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
                driver, search_keyword, max_results, min_price, return_driver, max_pages
            )
        else:
            return _search_with_form(
                driver, search_keyword, max_results, min_price, return_driver, max_pages
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
    return_driver: bool,
    max_pages: Optional[int] = None
) -> Union[List[Dict], Tuple[List[Dict], WebDriver], Tuple[List[Dict], None]]:
    """직접 URL 접근 방식으로 검색 (페이지네이션 지원)"""
    try:
        logger.info(f"검색어 '{search_keyword}'로 직접 URL 접근...")
        encoded_keyword = quote(search_keyword, safe='')
        
        all_results = []
        seen_product_ids = set()  # 중복 제거용
        current_page = 1
        max_pages_to_fetch = max_pages if max_pages else 1
        
        while current_page <= max_pages_to_fetch:
            # 페이지 URL 생성
            if current_page == 1:
                search_url = SEARCH_URL_TEMPLATE.format(keyword=encoded_keyword)
            else:
                search_url = SEARCH_URL_TEMPLATE_WITH_PAGE.format(
                    keyword=encoded_keyword, page=current_page
                )
            
            logger.info(f"[페이지 {current_page}/{max_pages_to_fetch}] 검색 URL 접근: {search_url}")
            driver.get(search_url)
            
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
            page_results = parse_search_results(driver, max_results=None, min_price=min_price)
            
            if not page_results:
                logger.info(f"페이지 {current_page}에서 결과가 없습니다. 페이지네이션 종료.")
                break
            
            # 중복 제거 및 결과 추가
            new_results = []
            for product in page_results:
                product_id = product.get('product_id')
                if product_id and product_id not in seen_product_ids:
                    seen_product_ids.add(product_id)
                    new_results.append(product)
                elif not product_id:
                    # product_id가 없으면 이름으로 중복 체크
                    product_name = product.get('name', '')
                    if product_name and product_name not in seen_product_ids:
                        seen_product_ids.add(product_name)
                        new_results.append(product)
            
            all_results.extend(new_results)
            logger.info(f"페이지 {current_page}: {len(new_results)}개 상품 추가 (총 {len(all_results)}개)")
            
            # max_results 제한 확인
            if max_results and len(all_results) >= max_results:
                all_results = all_results[:max_results]
                logger.info(f"최대 결과 수({max_results})에 도달했습니다.")
                break
            
            # 다음 페이지가 있는지 확인
            if not _has_next_page(driver):
                logger.info("더 이상 페이지가 없습니다.")
                break
            
            current_page += 1
            
            # 페이지 간 대기
            time.sleep(WAIT_TIMES['page_load'])
        
        _log_search_complete(all_results, min_price)
        
        if return_driver:
            return all_results, driver
        return all_results
        
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
    return_driver: bool,
    max_pages: Optional[int] = None
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
        
        # 첫 페이지 결과 파싱
        all_results = []
        seen_product_ids = set()
        current_page = 1
        max_pages_to_fetch = max_pages if max_pages else 1
        
        while current_page <= max_pages_to_fetch:
            # 검색 결과 파싱
            page_results = parse_search_results(driver, max_results=None, min_price=min_price)
            
            if not page_results:
                logger.info(f"페이지 {current_page}에서 결과가 없습니다.")
                break
            
            # 중복 제거 및 결과 추가
            new_results = []
            for product in page_results:
                product_id = product.get('product_id')
                if product_id and product_id not in seen_product_ids:
                    seen_product_ids.add(product_id)
                    new_results.append(product)
                elif not product_id:
                    product_name = product.get('name', '')
                    if product_name and product_name not in seen_product_ids:
                        seen_product_ids.add(product_name)
                        new_results.append(product)
            
            all_results.extend(new_results)
            logger.info(f"페이지 {current_page}: {len(new_results)}개 상품 추가 (총 {len(all_results)}개)")
            
            # max_results 제한 확인
            if max_results and len(all_results) >= max_results:
                all_results = all_results[:max_results]
                logger.info(f"최대 결과 수({max_results})에 도달했습니다.")
                break
            
            # 다음 페이지로 이동 시도
            if current_page < max_pages_to_fetch:
                if not _navigate_to_next_page(driver):
                    logger.info("더 이상 페이지가 없습니다.")
                    break
                current_page += 1
                time.sleep(WAIT_TIMES['page_load'])
            else:
                break
        
        _log_search_complete(all_results, min_price)
        
        if return_driver:
            return all_results, driver
        return all_results
        
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

def _has_next_page(driver: WebDriver) -> bool:
    """다음 페이지가 있는지 확인 (URL 파라미터 방식)"""
    try:
        # 현재 URL에서 페이지 번호 추출
        current_url = driver.current_url
        if 'page=' in current_url:
            # 이미 페이지 파라미터가 있으면 다음 페이지 URL 생성 가능
            return True
        
        # 다음 페이지 버튼이 있는지 확인
        from utils import find_element_by_selectors
        next_button = find_element_by_selectors(
            driver, SELECTORS['search']['pagination']['next_page']
        )
        return next_button is not None
    except:
        return False

def _navigate_to_next_page(driver: WebDriver) -> bool:
    """다음 페이지로 이동 (버튼 클릭 방식)"""
    try:
        from utils import find_element_by_selectors, safe_click
        
        # 다음 페이지 버튼 찾기
        next_button = find_element_by_selectors(
            driver, SELECTORS['search']['pagination']['next_page']
        )
        
        if next_button:
            # 버튼이 비활성화되어 있는지 확인
            if not next_button.is_enabled():
                return False
            
            # 다음 페이지로 스크롤
            from utils import scroll_to_element
            scroll_to_element(driver, next_button)
            time.sleep(WAIT_TIMES['element'])
            
            # 버튼 클릭
            if safe_click(driver, next_button):
                # 페이지 로딩 대기
                _wait_for_search_results(driver)
                _scroll_page(driver)
                time.sleep(WAIT_TIMES['page_load'])
                return True
        
        # 페이지 번호 링크로 시도
        try:
            # 현재 페이지 번호 찾기
            current_page_elem = find_element_by_selectors(
                driver, SELECTORS['search']['pagination']['current_page']
            )
            
            current_page_num = 1
            if current_page_elem:
                try:
                    current_page_text = current_page_elem.text.strip()
                    if current_page_text.isdigit():
                        current_page_num = int(current_page_text)
                except:
                    pass
            
            # 다음 페이지 번호 계산
            page_links = driver.find_elements(
                By.CSS_SELECTOR, SELECTORS['search']['pagination']['page_numbers'][0]
            )
            for link in page_links:
                try:
                    link_text = link.text.strip()
                    if link_text.isdigit():
                        link_page = int(link_text)
                        # 현재 페이지보다 큰 첫 번째 링크 클릭
                        if link_page > current_page_num:
                            scroll_to_element(driver, link)
                            time.sleep(WAIT_TIMES['element'])
                            if safe_click(driver, link):
                                _wait_for_search_results(driver)
                                _scroll_page(driver)
                                time.sleep(WAIT_TIMES['page_load'])
                                return True
                except:
                    continue
        except:
            pass
        
        return False
    except Exception as e:
        logger.debug(f"다음 페이지 이동 실패: {e}")
        return False

def _log_search_complete(results: List[Dict], min_price: Optional[int]) -> None:
    """검색 완료 로그 출력"""
    if min_price:
        logger.info(f"검색 완료! {min_price:,}원 이상 상품 {len(results)}개 발견")
    else:
        logger.info(f"검색 완료! 총 {len(results)}개 결과 발견")

