"""
마이박스 관련 기능 모듈
"""
from typing import Optional, List
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time

from config import SPEEDGO_URL, MYBOX_URL, SELECTORS, WAIT_TIMES
from utils import find_element_by_selectors, safe_click, scroll_to_element
from logger import default_logger as logger

def add_products_to_mybox(
    driver: WebDriver,
    product_ids: Optional[List[str]] = None,
    select_all: bool = False
) -> bool:
    """
    검색 결과에서 상품을 선택하고 마이박스에 담기
    
    Args:
        driver: Selenium WebDriver 객체
        product_ids: 선택할 상품번호 리스트 (None이면 모든 상품 선택)
        select_all: True면 모든 상품 선택
    
    Returns:
        성공 여부
    """
    try:
        logger.info("마이박스에 상품 추가 중...")
        
        # 상품 선택
        if not _select_products(driver, product_ids, select_all):
            logger.error("상품 선택 실패")
            return False
        
        # 마이박스담기 버튼 클릭
        if not _click_mybox_button(driver):
            logger.error("마이박스담기 버튼 클릭 실패")
            return False
        
        # 스피드고 사이트로 이동
        _navigate_to_speedgo(driver)
        
        # 마이박스 페이지로 이동
        _navigate_to_mybox(driver)
        
        # 전체 선택 및 스피드고전송
        return _send_to_speedgo(driver)
        
    except Exception as e:
        logger.error(f"마이박스담기 중 오류 발생: {e}", exc_info=True)
        return False

def _select_products(driver: WebDriver, product_ids: Optional[List[str]], select_all: bool) -> bool:
    """상품 선택"""
    if select_all:
        try:
            select_all_btn = driver.find_element(
                By.CSS_SELECTOR,
                "input[type='checkbox'][onclick*='all'], input[type='checkbox'][id*='all']"
            )
            if not select_all_btn.is_selected():
                select_all_btn.click()
                logger.info("전체 선택")
                time.sleep(WAIT_TIMES['element'])
        except:
            pass
    
    if product_ids:
        selected_count = 0
        for product_id in product_ids:
            if _select_single_product(driver, product_id):
                selected_count += 1
        
        if selected_count == 0:
            logger.error("선택된 상품이 없습니다.")
            return False
        
        logger.info(f"{selected_count}개 상품 선택 완료")
    else:
        # 모든 체크박스 선택
        try:
            checkboxes = driver.find_elements(By.CSS_SELECTOR, SELECTORS['product']['checkbox'])
            selected_count = 0
            for checkbox in checkboxes:
                if not checkbox.is_selected():
                    scroll_to_element(driver, checkbox)
                    time.sleep(WAIT_TIMES['scroll'])
                    checkbox.click()
                    selected_count += 1
            logger.info(f"{selected_count}개 상품 선택")
        except Exception as e:
            logger.error(f"체크박스 선택 중 오류: {e}")
            return False
    
    return True

def _select_single_product(driver: WebDriver, product_id: str) -> bool:
    """단일 상품 선택"""
    checkbox_selectors = [
        f"input[type='checkbox'][value='{product_id}']",
        f"input[type='checkbox'][name='item[]'][value='{product_id}']",
        f"input[type='checkbox'][id='{product_id}']",
        f"#input_check3_{product_id}",
    ]
    
    checkbox = find_element_by_selectors(driver, checkbox_selectors)
    if not checkbox:
        logger.warning(f"상품 {product_id} 체크박스를 찾을 수 없음")
        return False
    
    if checkbox.is_selected():
        logger.debug(f"상품 {product_id} 이미 선택됨")
        return True
    
    scroll_to_element(driver, checkbox)
    time.sleep(WAIT_TIMES['click'])
    
    if safe_click(driver, checkbox):
        time.sleep(WAIT_TIMES['element'])
        if checkbox.is_selected():
            logger.debug(f"상품 {product_id} 선택 성공")
            return True
    
    logger.warning(f"상품 {product_id} 선택 실패")
    return False

def _click_mybox_button(driver: WebDriver) -> bool:
    """마이박스담기 버튼 클릭"""
    logger.info("마이박스담기 버튼 찾는 중...")
    
    # onclick="hashTagAdd()"를 가진 버튼 찾기
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, "button[onclick*='hashTagAdd']")
        for btn in buttons:
            onclick_attr = btn.get_attribute('onclick') or ''
            if 'hashTagAdd' in onclick_attr and 'itemSave' not in onclick_attr:
                scroll_to_element(driver, btn)
                time.sleep(WAIT_TIMES['element'])
                if safe_click(driver, btn):
                    logger.info("마이박스담기 버튼 클릭 성공")
                    time.sleep(WAIT_TIMES['action_complete'])
                    
                    # Alert 처리 (마이박스에 저장되었습니다)
                    try:
                        from selenium.webdriver.common.alert import Alert
                        alert = driver.switch_to.alert
                        alert_text = alert.text
                        logger.info(f"Alert 감지: {alert_text}")
                        alert.accept()
                        logger.info("Alert 닫기 완료")
                        time.sleep(WAIT_TIMES['element'])
                    except Exception as e:
                        # Alert가 없으면 정상적으로 진행
                        logger.debug(f"Alert 없음 또는 이미 닫힘: {e}")
                    
                    return True
    except Exception as e:
        logger.error(f"마이박스담기 버튼 클릭 실패: {e}")
    
    return False

def _navigate_to_speedgo(driver: WebDriver) -> None:
    """스피드고 사이트로 이동"""
    logger.info("스피드고 사이트로 이동 중...")
    
    # Alert가 있을 수 있으므로 먼저 처리
    try:
        from selenium.webdriver.common.alert import Alert
        alert = driver.switch_to.alert
        alert_text = alert.text
        logger.info(f"Alert 감지: {alert_text}")
        alert.accept()
        logger.info("Alert 닫기 완료")
        time.sleep(WAIT_TIMES['element'])
    except Exception as e:
        # Alert가 없으면 정상적으로 진행
        logger.debug(f"Alert 없음: {e}")
    
    driver.get(SPEEDGO_URL)
    
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    time.sleep(WAIT_TIMES['page_load'])
    logger.info(f"스피드고 사이트 접속 완료: {driver.current_url}")

def _navigate_to_mybox(driver: WebDriver) -> None:
    """마이박스 페이지로 이동"""
    logger.info("마이박스 메뉴 클릭 중...")
    
    mybox_link = find_element_by_selectors(driver, [SELECTORS['mybox']['link']])
    
    if mybox_link:
        scroll_to_element(driver, mybox_link)
        time.sleep(WAIT_TIMES['element'])
        mybox_link.click()
        time.sleep(WAIT_TIMES['page_load'])
        logger.info("마이박스 메뉴 클릭 완료")
    else:
        # 직접 URL로 이동
        driver.get(MYBOX_URL)
        time.sleep(WAIT_TIMES['page_load'])
        logger.info("마이박스 페이지로 직접 이동")

def _send_to_speedgo(driver: WebDriver) -> bool:
    """전체 선택 및 스피드고전송"""
    logger.info("전체 선택 및 스피드고전송 준비 중...")
    time.sleep(WAIT_TIMES['page_load'])
    
    # 전체 선택
    if not _select_all_in_mybox(driver):
        logger.warning("전체 선택 실패")
    
    # 스피드고전송 버튼 클릭
    if not _click_speedgo_button(driver):
        logger.error("스피드고전송 버튼 클릭 실패")
        return False
    
    # 팝업에서 두 번째 스피드고전송 버튼 클릭
    return _click_speedgo_button2(driver)

def _select_all_in_mybox(driver: WebDriver) -> bool:
    """마이박스에서 전체 선택"""
    try:
        # 여러 선택자 시도
        select_all_selectors = [
            ("id", SELECTORS['mybox']['select_all']),
            ("css", "input#selectAll"),
            ("css", "input[name='selectAll']"),
            ("css", "input.checkbox1#selectAll"),
            ("css", "input[type='checkbox'][id='selectAll']"),
        ]
        
        select_all_checkbox = None
        for selector_type, selector in select_all_selectors:
            try:
                if selector_type == "id":
                    select_all_checkbox = driver.find_element(By.ID, selector)
                else:
                    select_all_checkbox = driver.find_element(By.CSS_SELECTOR, selector)
                logger.debug(f"전체 선택 체크박스 찾음: {selector_type}={selector}")
                break
            except:
                continue
        
        if not select_all_checkbox:
            logger.warning("전체 선택 체크박스를 찾을 수 없습니다.")
            return False
        
        if select_all_checkbox.is_selected():
            logger.info("전체 선택 체크박스가 이미 선택되어 있습니다.")
            return True
        
        scroll_to_element(driver, select_all_checkbox)
        time.sleep(WAIT_TIMES['element'])
        
        # 여러 방법으로 클릭 시도
        if safe_click(driver, select_all_checkbox):
            time.sleep(WAIT_TIMES['element'])
            if select_all_checkbox.is_selected():
                logger.info("전체 선택 완료")
                return True
        
        # JavaScript로 강제 선택
        try:
            driver.execute_script("arguments[0].checked = true;", select_all_checkbox)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", select_all_checkbox)
            time.sleep(WAIT_TIMES['element'])
            if select_all_checkbox.is_selected():
                logger.info("전체 선택 완료 (JavaScript 강제 선택)")
                return True
        except Exception as e:
            logger.debug(f"JavaScript 강제 선택 실패: {e}")
        
    except Exception as e:
        logger.debug(f"전체 선택 실패: {e}")
    
    return False

def _click_speedgo_button(driver: WebDriver) -> bool:
    """스피드고전송 버튼 클릭"""
    logger.info("스피드고전송 버튼 찾는 중...")
    
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, "button[onclick*='speedGoSend']")
        for btn in buttons:
            onclick_attr = btn.get_attribute('onclick') or ''
            if 'speedGoSend' in onclick_attr:
                scroll_to_element(driver, btn)
                time.sleep(WAIT_TIMES['element'])
                if safe_click(driver, btn):
                    logger.info("스피드고전송 버튼 클릭 성공")
                    # 팝업이 나타날 때까지 대기
                    time.sleep(WAIT_TIMES['popup'])
                    return True
    except Exception as e:
        logger.error(f"스피드고전송 버튼 클릭 실패: {e}")
    
    return False

def _click_speedgo_button2(driver: WebDriver) -> bool:
    """팝업 창 내부에서 두 번째 스피드고전송 버튼 클릭"""
    logger.info("팝업 창 내부에서 두 번째 스피드고전송 버튼 찾는 중...")
    
    # 팝업이 나타날 때까지 대기
    try:
        # 팝업 요소가 나타날 때까지 대기
        popup_selectors = [
            "iframe[id*='layui-layer-iframe']",
            "#mkForm",
            "div[style*='background:#2c303b']",
        ]
        
        popup_loaded = False
        for selector in popup_selectors:
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                logger.debug(f"팝업 요소 발견: {selector}")
                popup_loaded = True
                break
            except:
                continue
        
        if not popup_loaded:
            logger.warning("팝업 창이 감지되지 않았지만 계속 진행합니다...")
        
        time.sleep(WAIT_TIMES['popup'])  # 팝업 로딩 대기
    except Exception as e:
        logger.debug(f"팝업 대기 중 오류: {e}")
    
    # iframe으로 전환 시도
    iframe_switched = False
    try:
        # 여러 iframe 선택자 시도
        iframe_selectors = [
            "iframe[id*='layui-layer-iframe']",
            "iframe[name*='layui-layer-iframe']",
            "iframe[src*='popup_setBulkProduct']",
            "iframe",
        ]
        
        for iframe_selector in iframe_selectors:
            try:
                iframes = driver.find_elements(By.CSS_SELECTOR, iframe_selector)
                for iframe in iframes:
                    iframe_src = iframe.get_attribute('src') or ''
                    iframe_id = iframe.get_attribute('id') or ''
                    # popup_setBulkProduct가 포함되어 있거나 layui-layer-iframe이 포함된 경우
                    if 'popup_setBulkProduct' in iframe_src or 'layui-layer-iframe' in iframe_id:
                        driver.switch_to.frame(iframe)
                        iframe_switched = True
                        logger.info(f"iframe으로 전환 완료 (src: {iframe_src[:50]}...)")
                        time.sleep(WAIT_TIMES['iframe'])
                        break
                if iframe_switched:
                    break
            except Exception as e:
                logger.debug(f"iframe 전환 시도 실패 ({iframe_selector}): {e}")
                continue
    except Exception as e:
        logger.debug(f"iframe 전환 중 오류: {e}")
    
    try:
        # 버튼 찾기 (더 많은 선택자 시도)
        button_selectors = [
            ("xpath", "//*[@id='mkForm']/div/div[3]/div[11]/button[1]"),
            ("css", "#mkForm button[onclick*='goProduct']"),
            ("css", "button[onclick*='goProduct']"),
            ("css", "#mkForm button:first-child"),
            ("css", "#mkForm button"),
            ("xpath", "//button[contains(@onclick, 'goProduct')]"),
            ("xpath", "//button[contains(text(), '스피드고')]"),
        ]
        
        speedgo_button2 = None
        for selector_type, selector in button_selectors:
            try:
                if selector_type == "xpath":
                    speedgo_button2 = driver.find_element(By.XPATH, selector)
                else:
                    speedgo_button2 = driver.find_element(By.CSS_SELECTOR, selector)
                
                # 버튼이 보이는지 확인
                if speedgo_button2 and speedgo_button2.is_displayed():
                    logger.debug(f"버튼 찾음: {selector_type}={selector}")
                    break
            except Exception as e:
                logger.debug(f"버튼 찾기 실패 ({selector_type}={selector}): {e}")
                continue
        
        if not speedgo_button2:
            # 디버깅: mkForm 내부의 모든 버튼 출력
            try:
                mkform = driver.find_element(By.ID, "mkForm")
                all_buttons = mkform.find_elements(By.TAG_NAME, "button")
                logger.debug(f"mkForm 내부 버튼 개수: {len(all_buttons)}")
                for i, btn in enumerate(all_buttons[:5], 1):
                    logger.debug(f"  버튼 {i}: 텍스트='{btn.text}', onclick='{btn.get_attribute('onclick') or ''}'")
            except:
                pass
            
            logger.error("두 번째 스피드고전송 버튼을 찾을 수 없습니다.")
            return False
        
        scroll_to_element(driver, speedgo_button2)
        time.sleep(WAIT_TIMES['element'])
        
        if safe_click(driver, speedgo_button2):
            logger.info("두 번째 스피드고전송 버튼 클릭 성공")
            time.sleep(WAIT_TIMES['action_complete'])
            return True
        else:
            logger.error("두 번째 스피드고전송 버튼 클릭 실패")
            
    except Exception as e:
        logger.error(f"두 번째 스피드고전송 버튼 클릭 실패: {e}", exc_info=True)
    finally:
        if iframe_switched:
            try:
                driver.switch_to.default_content()
                logger.debug("기본 컨텍스트로 복귀")
            except:
                pass
    
    return False

