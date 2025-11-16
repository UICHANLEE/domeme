"""
도매꾹 로그인 모듈
"""
import getpass
from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time

from config import LOGIN_URL_BASE, LOGIN_BACK_URL_BASE64, SELECTORS, WAIT_TIMES, get_username, get_password
from logger import default_logger as logger

def login_to_domeggook(
    driver: WebDriver,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> bool:
    """
    도매꾹 사이트에 로그인
    
    Args:
        driver: Selenium WebDriver 객체
        username: 로그인 아이디 (None이면 환경변수 또는 사용자 입력)
        password: 비밀번호 (None이면 환경변수 또는 사용자 입력)
    
    Returns:
        로그인 성공 여부
    """
    try:
        # 환경변수에서 로그인 정보 읽기
        if not username:
            username = get_username()
        if not password:
            password = get_password()
        
        # 로그인 페이지로 이동
        login_url = f"{LOGIN_URL_BASE}?back={LOGIN_BACK_URL_BASE64}"
        logger.info(f"로그인 페이지로 이동: {login_url}")
        driver.get(login_url)
        
        # 페이지 로딩 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(WAIT_TIMES['page_load'])
        
        # 로그인 정보 입력 받기
        if not username:
            username = input("아이디를 입력하세요: ").strip()
        if not password:
            password = getpass.getpass("비밀번호를 입력하세요: ").strip()
        
        if not username or not password:
            logger.error("아이디와 비밀번호가 필요합니다.")
            return False
        
        # 로그인 폼 요소 찾기
        user_id_input = _find_element_by_selectors(driver, SELECTORS['login']['user_id'])
        password_input = _find_element_by_selectors(driver, SELECTORS['login']['password'])
        
        if not user_id_input or not password_input:
            logger.error("로그인 폼을 찾을 수 없습니다.")
            return False
        
        # 로그인 정보 입력
        user_id_input.clear()
        user_id_input.send_keys(username)
        time.sleep(WAIT_TIMES['element'])
        
        password_input.clear()
        password_input.send_keys(password)
        time.sleep(WAIT_TIMES['element'])
        
        # 로그인 버튼 찾기 및 클릭
        login_button = _find_element_by_selectors(driver, SELECTORS['login']['login_button'])
        
        if not login_button:
            password_input.send_keys(Keys.RETURN)
            logger.info("Enter 키로 로그인 시도")
        else:
            login_button.click()
            logger.info("로그인 버튼 클릭")
        
        # 로그인 완료 대기
        time.sleep(WAIT_TIMES['action_complete'])
        
        # 로그인 성공 확인
        return _verify_login_success(driver)
        
    except Exception as e:
        logger.error(f"로그인 중 오류 발생: {e}", exc_info=True)
        return False

def _find_element_by_selectors(driver: WebDriver, selectors: list):
    """여러 선택자 중 하나로 요소 찾기"""
    for selector in selectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            logger.debug(f"요소 찾음: {selector}")
            return element
        except NoSuchElementException:
            continue
    return None

def _verify_login_success(driver: WebDriver) -> bool:
    """로그인 성공 여부 확인"""
    current_url = driver.current_url
    
    # URL 기반 확인
    if "domemedb" in current_url.lower() or "mainChannel" in current_url.lower():
        logger.info("로그인 성공! (URL 확인)")
        return True
    
    if "login" not in current_url.lower():
        logger.info("로그인 성공! (로그인 페이지에서 이동)")
        return True
    
    # 로그아웃/마이페이지 링크 확인
    try:
        logout_elements = driver.find_elements(
            By.CSS_SELECTOR,
            "a[href*='logout'], a[href*='mypage'], [class*='logout'], [class*='mypage']"
        )
        if logout_elements:
            logger.info("로그인 성공! (로그아웃/마이페이지 링크 확인)")
            return True
    except:
        pass
    
    # 로그인 실패 메시지 확인
    try:
        error_selectors = [
            ".error", ".alert", "[class*='error']", "[class*='alert']",
            "[class*='fail']", "[class*='warning']", ".msg-error"
        ]
        for selector in error_selectors:
            try:
                error_msg = driver.find_element(By.CSS_SELECTOR, selector)
                error_text = error_msg.text.strip()
                if error_text:
                    logger.error(f"로그인 실패: {error_text}")
                    return False
            except:
                continue
    except:
        pass
    
    logger.error(f"로그인 실패: 로그인 상태를 확인할 수 없습니다. 현재 URL: {current_url}")
    return False

