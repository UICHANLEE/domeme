"""
도매꾹 사이트 접속 및 스크래핑을 위한 메인 스크립트
"""
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import re
import os
from urllib.parse import quote, urlparse, parse_qs


def access_with_requests():
    """requests 라이브러리를 사용한 간단한 접속"""
    url = "https://domemedb.domeggook.com/index/?mainChannel=aihome"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print(f"requests로 {url} 접속 시도 중...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        print(f"✓ 접속 성공! 상태 코드: {response.status_code}")
        print(f"✓ 페이지 제목: {BeautifulSoup(response.text, 'html.parser').title.string if response.text else 'N/A'}")
        
        return response
    except requests.exceptions.RequestException as e:
        print(f"✗ 접속 실패: {e}")
        return None


def get_chrome_driver(headless=True):
    """Chrome WebDriver 설정 및 반환"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')  # 헤드리스 모드 (브라우저 창 숨김)
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    return webdriver.Chrome(options=chrome_options)


def login_to_domeggook(driver, username=None, password=None):
    """
    도매꾹 사이트에 로그인
    
    Args:
        driver: Selenium WebDriver 객체
        username: 로그인 아이디 (None이면 사용자 입력 요청, 환경변수 DOMEID에서도 읽음)
        password: 비밀번호 (None이면 사용자 입력 요청, 환경변수 DOMPWD에서도 읽음)
    
    Returns:
        로그인 성공 여부 (bool)
    """
    import os
    
    try:
        # 환경변수에서 로그인 정보 읽기 (선택사항)
        if not username:
            username = os.getenv('DOMEID')
        if not password:
            password = os.getenv('DOMPWD')
        
        # 로그인 페이지로 이동 (올바른 URL 사용)
        # back 파라미터는 로그인 후 돌아갈 페이지를 지정 (base64 인코딩된 URL)
        back_url = "aHR0cHM6Ly9kb21lbWVkYi5kb21lZ2dvb2suY29tL2luZGV4"  # domemedb.domeggook.com/index를 base64 인코딩
        login_url = f"https://domeggook.com/ssl/member/mem_loginForm.php?back={back_url}"
        print(f"\n로그인 페이지로 이동: {login_url}")
        driver.get(login_url)
        
        # 페이지 로딩 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(1)
        
        # 로그인 정보 입력 받기
        if not username:
            username = input("아이디를 입력하세요: ").strip()
        if not password:
            import getpass
            password = getpass.getpass("비밀번호를 입력하세요: ").strip()
        
        if not username or not password:
            print("✗ 아이디와 비밀번호가 필요합니다.")
            return False
        
        # 로그인 폼 요소 찾기
        # 다양한 선택자 시도 (도매꾹 통합 로그인 페이지)
        user_id_selectors = [
            "input[name='user_id']",
            "input[name='id']",
            "input[name='username']",
            "input[name='mem_id']",
            "input[type='text'][id*='id']",
            "input[type='text'][id*='user']",
            "input[type='text'][id*='mem']",
            "#user_id",
            "#id",
            "#mem_id",
            "input[placeholder*='아이디']",
            "input[placeholder*='ID']",
        ]
        
        password_selectors = [
            "input[name='password']",
            "input[name='pwd']",
            "input[name='mem_pwd']",
            "input[type='password']",
            "#password",
            "#pwd",
            "#mem_pwd",
            "input[placeholder*='비밀번호']",
            "input[placeholder*='Password']",
        ]
        
        user_id_input = None
        password_input = None
        
        # 아이디 입력 필드 찾기
        for selector in user_id_selectors:
            try:
                user_id_input = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"✓ 아이디 입력 필드 찾음: {selector}")
                break
            except NoSuchElementException:
                continue
        
        # 비밀번호 입력 필드 찾기
        for selector in password_selectors:
            try:
                password_input = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"✓ 비밀번호 입력 필드 찾음: {selector}")
                break
            except NoSuchElementException:
                continue
        
        if not user_id_input or not password_input:
            print("✗ 로그인 폼을 찾을 수 없습니다.")
            # 페이지 소스 일부 출력 (디버깅용)
            try:
                page_source = driver.page_source[:2000]
                print(f"페이지 소스 샘플:\n{page_source}")
            except:
                pass
            return False
        
        # 로그인 정보 입력
        user_id_input.clear()
        user_id_input.send_keys(username)
        time.sleep(0.5)
        
        password_input.clear()
        password_input.send_keys(password)
        time.sleep(0.5)
        
        # 로그인 버튼 찾기 및 클릭
        login_button_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button.btn-login",
            "button[class*='login']",
            ".login-btn",
            "#loginBtn",
            "button:contains('로그인')",
            "a[href*='login']",
            "input[value*='로그인']",
            "button:contains('로그인')",
            "[onclick*='login']",
        ]
        
        login_button = None
        for selector in login_button_selectors:
            try:
                login_button = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"✓ 로그인 버튼 찾음: {selector}")
                break
            except NoSuchElementException:
                continue
        
        if not login_button:
            # Enter 키로 로그인 시도
            password_input.send_keys(Keys.RETURN)
            print("✓ Enter 키로 로그인 시도")
        else:
            login_button.click()
            print("✓ 로그인 버튼 클릭")
        
        # 로그인 완료 대기
        time.sleep(3)
        
        # 로그인 성공 확인 (URL 변경 또는 특정 요소 확인)
        current_url = driver.current_url
        
        # 로그인 성공 조건:
        # 1. login 관련 URL이 아니거나
        # 2. domemedb.domeggook.com으로 리다이렉트되었거나
        # 3. 로그아웃 버튼이나 마이페이지 링크가 있는 경우
        if "login" not in current_url.lower() or "domemedb" in current_url.lower() or "mainChannel" in current_url.lower():
            # 추가 확인: 로그아웃 버튼이나 마이페이지 링크 확인
            try:
                logout_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='logout'], a[href*='mypage'], [class*='logout'], [class*='mypage']")
                if logout_elements:
                    print("✓ 로그인 성공! (로그아웃/마이페이지 링크 확인)")
                    return True
            except:
                pass
            
            # URL 기반 확인
            if "domemedb" in current_url.lower() or "mainChannel" in current_url.lower():
                print("✓ 로그인 성공! (URL 확인)")
                return True
            elif "login" not in current_url.lower():
                print("✓ 로그인 성공! (로그인 페이지에서 이동)")
                return True
        
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
                        print(f"✗ 로그인 실패: {error_text}")
                        return False
                except:
                    continue
        except:
            pass
        
        print("✗ 로그인 실패: 로그인 상태를 확인할 수 없습니다.")
        print(f"  현재 URL: {current_url}")
        return False
            
    except Exception as e:
        print(f"✗ 로그인 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def access_with_selenium(headless=True):
    """Selenium을 사용한 브라우저 자동화 접속"""
    url = "https://domemedb.domeggook.com/index/?mainChannel=aihome"
    
    driver = None
    try:
        print(f"Selenium으로 {url} 접속 시도 중...")
        driver = get_chrome_driver(headless=headless)
        driver.get(url)
        
        # 페이지 로딩 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        print(f"✓ 접속 성공!")
        print(f"✓ 페이지 제목: {driver.title}")
        print(f"✓ 현재 URL: {driver.current_url}")
        
        return driver
    except Exception as e:
        print(f"✗ 접속 실패: {e}")
        print("ChromeDriver가 설치되어 있는지 확인하세요.")
        if driver:
            driver.quit()
        return None


def add_products_to_mybox(driver, product_ids=None, select_all=False):
    """
    검색 결과에서 상품을 선택하고 마이박스에 담기
    
    Args:
        driver: Selenium WebDriver 객체
        product_ids: 선택할 상품번호 리스트 (None이면 모든 상품 선택)
        select_all: True면 모든 상품 선택
    
    Returns:
        성공 여부 (bool)
    """
    try:
        print("\n마이박스에 상품 추가 중...")
        
        if select_all:
            # 전체 선택 버튼 찾기 (있는 경우)
            try:
                select_all_btn = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox'][onclick*='all'], input[type='checkbox'][id*='all'], input[type='checkbox'][name*='all']")
                if not select_all_btn.is_selected():
                    select_all_btn.click()
                    print("✓ 전체 선택")
                    time.sleep(0.5)
            except:
                pass
        
        # 개별 상품 체크박스 선택
        if product_ids:
            selected_count = 0
            for product_id in product_ids:
                try:
                    # 체크박스 찾기 (여러 방법 시도)
                    checkbox_selectors = [
                        f"input[type='checkbox'][value='{product_id}']",
                        f"input[type='checkbox'][name='item[]'][value='{product_id}']",
                        f"input[type='checkbox'][id='{product_id}']",
                        f"label[for='{product_id}'] input[type='checkbox']",
                        f"#input_check3_{product_id}",
                        f"input.input_check3[value='{product_id}']",
                    ]
                    
                    checkbox = None
                    for selector in checkbox_selectors:
                        try:
                            checkbox = driver.find_element(By.CSS_SELECTOR, selector)
                            break
                        except NoSuchElementException:
                            continue
                    
                    if checkbox:
                        # 체크박스가 보이도록 스크롤
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
                        time.sleep(0.3)
                        
                        # 현재 선택 상태 확인
                        is_selected_before = checkbox.is_selected()
                        print(f"  상품 {product_id}: 선택 전 상태 = {is_selected_before}")
                        
                        if not is_selected_before:
                            # 체크박스 클릭 (여러 방법 시도)
                            clicked = False
                            
                            # 방법 1: label을 통해 클릭 (가장 안정적)
                            try:
                                label = driver.find_element(By.CSS_SELECTOR, f"label[for='{product_id}']")
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", label)
                                time.sleep(0.2)
                                label.click()
                                clicked = True
                                print(f"    → label 클릭 시도")
                            except Exception as e:
                                print(f"    → label 클릭 실패: {e}")
                            
                            # 방법 2: 체크박스 직접 클릭
                            if not clicked:
                                try:
                                    checkbox.click()
                                    clicked = True
                                    print(f"    → 체크박스 직접 클릭 시도")
                                except Exception as e:
                                    print(f"    → 체크박스 직접 클릭 실패: {e}")
                            
                            # 방법 3: JavaScript로 강제 클릭
                            if not clicked:
                                try:
                                    driver.execute_script("arguments[0].click();", checkbox)
                                    clicked = True
                                    print(f"    → JavaScript 클릭 시도")
                                except Exception as e:
                                    print(f"    → JavaScript 클릭 실패: {e}")
                            
                            time.sleep(0.5)
                            
                            # 클릭 후 선택 상태 확인
                            is_selected_after = checkbox.is_selected()
                            print(f"  상품 {product_id}: 선택 후 상태 = {is_selected_after}")
                            
                            if is_selected_after:
                                selected_count += 1
                                print(f"✓ 상품 {product_id} 선택 성공!")
                            else:
                                # 강제로 체크 상태 변경 시도
                                try:
                                    driver.execute_script("arguments[0].checked = true;", checkbox)
                                    driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", checkbox)
                                    time.sleep(0.3)
                                    is_selected_final = checkbox.is_selected()
                                    if is_selected_final:
                                        selected_count += 1
                                        print(f"✓ 상품 {product_id} 강제 선택 성공!")
                                    else:
                                        print(f"✗ 상품 {product_id} 선택 실패 (강제 시도 후에도 실패)")
                                except Exception as e:
                                    print(f"✗ 상품 {product_id} 강제 선택 실패: {e}")
                        else:
                            selected_count += 1
                            print(f"✓ 상품 {product_id} 이미 선택됨")
                    else:
                        print(f"✗ 상품 {product_id} 체크박스를 찾을 수 없음")
                except Exception as e:
                    print(f"✗ 상품 {product_id} 선택 실패: {e}")
                    continue
            
            if selected_count == 0:
                print("✗ 선택된 상품이 없습니다.")
                return False
        else:
            # product_ids가 없으면 모든 체크박스 선택 시도
            try:
                checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox'][name='item[]']")
                selected_count = 0
                for checkbox in checkboxes:
                    if not checkbox.is_selected():
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                            time.sleep(0.1)
                            checkbox.click()
                            selected_count += 1
                        except:
                            pass
                print(f"✓ {selected_count}개 상품 선택")
            except Exception as e:
                print(f"✗ 체크박스 선택 중 오류: {e}")
                return False
        
        # 선택된 체크박스 개수 확인
        try:
            selected_checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox'][name='item[]']:checked")
            print(f"\n✓ 현재 선택된 체크박스 개수: {len(selected_checkboxes)}개")
            if len(selected_checkboxes) == 0:
                print("⚠ 경고: 선택된 체크박스가 없습니다!")
                return False
        except Exception as e:
            print(f"⚠ 체크박스 확인 중 오류: {e}")
        
        time.sleep(1)
        
        # 마이박스담기 버튼 찾기 및 클릭
        print("\n마이박스담기 버튼 찾는 중...")
        
        # 중요: onclick="hashTagAdd()"를 가진 버튼만 찾기 (선택상품DB담기는 onclick="itemSave()")
        mybox_button = None
        
        # 방법 1: onclick="hashTagAdd()" 속성으로 정확히 찾기
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, "button[onclick*='hashTagAdd']")
            for btn in buttons:
                onclick_attr = btn.get_attribute('onclick') or ''
                btn_text = btn.text.strip()
                # hashTagAdd 함수를 호출하는 버튼인지 확인
                if 'hashTagAdd' in onclick_attr and 'itemSave' not in onclick_attr:
                    mybox_button = btn
                    print(f"✓ 마이박스담기 버튼 찾음 (onclick='hashTagAdd')")
                    print(f"  버튼 텍스트: '{btn_text}'")
                    print(f"  onclick 속성: '{onclick_attr}'")
                    break
        except Exception as e:
            print(f"  onclick 검색 중 오류: {e}")
        
        # 방법 2: 텍스트로 찾기 (백업)
        if not mybox_button:
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                print(f"  전체 버튼 개수: {len(buttons)}개")
                for btn in buttons:
                    btn_text = btn.text.strip()
                    btn_onclick = btn.get_attribute('onclick') or ''
                    # "마이박스담기" 텍스트가 있고 hashTagAdd 함수를 호출하는 버튼
                    if ("마이박스담기" in btn_text or "마이박스" in btn_text) and "hashTagAdd" in btn_onclick:
                        mybox_button = btn
                        print(f"✓ 마이박스담기 버튼 찾음 (텍스트 + onclick 검색)")
                        print(f"  버튼 텍스트: '{btn_text}'")
                        print(f"  onclick 속성: '{btn_onclick}'")
                        break
            except Exception as e:
                print(f"  텍스트 검색 중 오류: {e}")
        
        # 방법 3: 클래스와 onclick 조합으로 찾기
        if not mybox_button:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, "button.footer_position_btn1")
                for btn in buttons:
                    btn_onclick = btn.get_attribute('onclick') or ''
                    btn_text = btn.text.strip()
                    # footer_position_btn1 클래스를 가진 버튼 중 hashTagAdd를 호출하는 것
                    if 'hashTagAdd' in btn_onclick and 'itemSave' not in btn_onclick:
                        mybox_button = btn
                        print(f"✓ 마이박스담기 버튼 찾음 (클래스 + onclick 검색)")
                        print(f"  버튼 텍스트: '{btn_text}'")
                        print(f"  onclick 속성: '{btn_onclick}'")
                        break
            except Exception as e:
                print(f"  클래스 검색 중 오류: {e}")
        
        if not mybox_button:
            print("✗ 마이박스담기 버튼을 찾을 수 없습니다.")
            # 디버깅: 모든 버튼 출력
            try:
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                print(f"  페이지의 모든 버튼 ({len(all_buttons)}개):")
                for i, btn in enumerate(all_buttons[:10], 1):  # 처음 10개만
                    print(f"    {i}. 텍스트: '{btn.text.strip()}', onclick: '{btn.get_attribute('onclick') or ''}'")
            except:
                pass
            return False
        
        # 버튼이 보이도록 스크롤
        print("\n마이박스담기 버튼 클릭 시도...")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", mybox_button)
        time.sleep(0.5)
        
        # 버튼이 보이는지 확인
        is_displayed = mybox_button.is_displayed()
        is_enabled = mybox_button.is_enabled()
        print(f"  버튼 표시 여부: {is_displayed}")
        print(f"  버튼 활성화 여부: {is_enabled}")
        
        # 버튼 클릭 (여러 방법 시도)
        clicked = False
        
        # 방법 1: 직접 클릭
        try:
            mybox_button.click()
            clicked = True
            print("✓ 마이박스담기 버튼 클릭 (직접 클릭)")
        except Exception as e:
            print(f"  직접 클릭 실패: {e}")
        
        # 방법 2: JavaScript로 클릭
        if not clicked:
            try:
                driver.execute_script("arguments[0].click();", mybox_button)
                clicked = True
                print("✓ 마이박스담기 버튼 클릭 (JavaScript)")
            except Exception as e:
                print(f"  JavaScript 클릭 실패: {e}")
        
        # 방법 3: onclick 함수 직접 실행
        if not clicked:
            try:
                onclick_attr = mybox_button.get_attribute('onclick')
                if onclick_attr:
                    driver.execute_script(onclick_attr)
                    clicked = True
                    print("✓ 마이박스담기 버튼 클릭 (onclick 함수 직접 실행)")
            except Exception as e:
                print(f"  onclick 함수 실행 실패: {e}")
        
        if not clicked:
            print("✗ 마이박스담기 버튼 클릭 실패")
            return False
        
        # 처리 완료 대기
        print("\n마이박스담기 처리 대기 중...")
        time.sleep(3)
        
        # 성공 메시지 확인 (있는 경우)
        try:
            success_msg = driver.find_element(By.CSS_SELECTOR, ".success, .alert-success, [class*='success']")
            print(f"✓ 성공: {success_msg.text}")
        except:
            pass
        
        print("✓ 마이박스에 상품 추가 완료!")
        
        # 스피드고 사이트로 이동
        print("\n스피드고 사이트로 이동 중...")
        speedgo_url = "https://speedgo.domeggook.com/"
        driver.get(speedgo_url)
        
        # 페이지 로딩 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)
        print(f"✓ 스피드고 사이트 접속 완료: {driver.current_url}")
        
        # 마이박스 메뉴 클릭
        print("\n마이박스 메뉴 클릭 중...")
        mybox_selectors = [
            "a[href*='mybox/mb_saveList.php']",
            "a.cur[href*='mybox']",
            "a:contains('마이박스')",
        ]
        
        mybox_link = None
        for selector in mybox_selectors:
            try:
                mybox_link = driver.find_element(By.CSS_SELECTOR, selector)
                link_text = mybox_link.text.strip()
                link_href = mybox_link.get_attribute('href') or ''
                print(f"✓ 마이박스 링크 찾음: {selector}")
                print(f"  링크 텍스트: '{link_text}'")
                print(f"  링크 주소: '{link_href}'")
                break
            except NoSuchElementException:
                continue
        
        if not mybox_link:
            # 텍스트로 찾기 시도
            try:
                links = driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    link_text = link.text.strip()
                    link_href = link.get_attribute('href') or ''
                    if "마이박스" in link_text and "mybox" in link_href:
                        mybox_link = link
                        print(f"✓ 마이박스 링크 찾음 (텍스트 검색)")
                        print(f"  링크 텍스트: '{link_text}'")
                        print(f"  링크 주소: '{link_href}'")
                        break
            except Exception as e:
                print(f"  텍스트 검색 중 오류: {e}")
        
        if not mybox_link:
            print("✗ 마이박스 링크를 찾을 수 없습니다.")
            # 직접 URL로 이동 시도
            try:
                mybox_url = "https://speedgo.domeggook.com/mybox/mb_saveList.php"
                driver.get(mybox_url)
                print(f"✓ 마이박스 페이지로 직접 이동: {mybox_url}")
                time.sleep(2)
                return True
            except Exception as e:
                print(f"✗ 마이박스 페이지 이동 실패: {e}")
                return False
        
        # 링크 클릭
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", mybox_link)
            time.sleep(0.5)
            mybox_link.click()
            print("✓ 마이박스 메뉴 클릭 완료")
            time.sleep(2)
            
            # 페이지 이동 확인
            current_url = driver.current_url
            if "mybox" in current_url.lower():
                print(f"✓ 마이박스 페이지 이동 완료: {current_url}")
            else:
                print(f"⚠ 현재 URL: {current_url} (마이박스 페이지가 아닐 수 있음)")
        except Exception as e:
            print(f"✗ 마이박스 메뉴 클릭 실패: {e}")
            # 직접 URL로 이동 시도
            try:
                mybox_url = "https://speedgo.domeggook.com/mybox/mb_saveList.php"
                driver.get(mybox_url)
                print(f"✓ 마이박스 페이지로 직접 이동: {mybox_url}")
                time.sleep(2)
            except:
                pass
        
        # 마이박스 페이지에서 전체 선택 및 스피드고전송
        print("\n마이박스 페이지에서 전체 선택 및 스피드고전송 준비 중...")
        time.sleep(2)
        
        # 전체 선택 체크박스 찾기 및 선택
        print("\n전체 선택 체크박스 찾는 중...")
        select_all_checkbox = None
        
        try:
            # id="selectAll" 체크박스 찾기
            select_all_checkbox = driver.find_element(By.ID, "selectAll")
            print("✓ 전체 선택 체크박스 찾음 (id='selectAll')")
        except NoSuchElementException:
            # 다른 선택자 시도
            try:
                select_all_checkbox = driver.find_element(By.CSS_SELECTOR, "input[name='selectAll']")
                print("✓ 전체 선택 체크박스 찾음 (name='selectAll')")
            except:
                try:
                    select_all_checkbox = driver.find_element(By.CSS_SELECTOR, "input.checkbox1#selectAll")
                    print("✓ 전체 선택 체크박스 찾음 (class='checkbox1' id='selectAll')")
                except:
                    pass
        
        if select_all_checkbox:
            # 체크박스 선택 상태 확인
            is_selected = select_all_checkbox.is_selected()
            print(f"  전체 선택 체크박스 현재 상태: {is_selected}")
            
            if not is_selected:
                # 체크박스가 보이도록 스크롤
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", select_all_checkbox)
                time.sleep(0.5)
                
                # 체크박스 클릭 시도
                clicked = False
                
                # 방법 1: label을 통해 클릭
                try:
                    label = driver.find_element(By.CSS_SELECTOR, "label[for='selectAll']")
                    label.click()
                    clicked = True
                    print("✓ 전체 선택 체크박스 클릭 (label 클릭)")
                except:
                    pass
                
                # 방법 2: 체크박스 직접 클릭
                if not clicked:
                    try:
                        select_all_checkbox.click()
                        clicked = True
                        print("✓ 전체 선택 체크박스 클릭 (직접 클릭)")
                    except:
                        pass
                
                # 방법 3: JavaScript로 클릭
                if not clicked:
                    try:
                        driver.execute_script("arguments[0].click();", select_all_checkbox)
                        clicked = True
                        print("✓ 전체 선택 체크박스 클릭 (JavaScript)")
                    except:
                        pass
                
                # 방법 4: 강제로 체크 상태 변경
                if not clicked:
                    try:
                        driver.execute_script("arguments[0].checked = true;", select_all_checkbox)
                        driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", select_all_checkbox)
                        print("✓ 전체 선택 체크박스 강제 선택")
                    except:
                        pass
                
                time.sleep(1)
                
                # 선택 상태 확인
                is_selected_after = select_all_checkbox.is_selected()
                print(f"  전체 선택 체크박스 선택 후 상태: {is_selected_after}")
                
                if is_selected_after:
                    print("✓ 전체 선택 완료!")
                else:
                    print("⚠ 전체 선택이 완료되지 않았을 수 있습니다.")
            else:
                print("✓ 전체 선택 체크박스가 이미 선택되어 있습니다.")
        else:
            print("✗ 전체 선택 체크박스를 찾을 수 없습니다.")
        
        time.sleep(1)
        
        # 스피드고전송 버튼 찾기 및 클릭
        print("\n스피드고전송 버튼 찾는 중...")
        speedgo_button = None
        
        # 방법 1: onclick="speedGoSend()" 속성으로 찾기
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, "button[onclick*='speedGoSend']")
            for btn in buttons:
                onclick_attr = btn.get_attribute('onclick') or ''
                if 'speedGoSend' in onclick_attr:
                    speedgo_button = btn
                    print("✓ 스피드고전송 버튼 찾음 (onclick='speedGoSend')")
                    break
        except Exception as e:
            print(f"  onclick 검색 중 오류: {e}")
        
        # 방법 2: 텍스트로 찾기
        if not speedgo_button:
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    btn_text = btn.text.strip()
                    btn_onclick = btn.get_attribute('onclick') or ''
                    if ("스피드고전송" in btn_text or "스피드고" in btn_text) and "speedGoSend" in btn_onclick:
                        speedgo_button = btn
                        print("✓ 스피드고전송 버튼 찾음 (텍스트 검색)")
                        break
            except Exception as e:
                print(f"  텍스트 검색 중 오류: {e}")
        
        # 방법 3: 클래스로 찾기
        if not speedgo_button:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, "button.button2")
                for btn in buttons:
                    btn_onclick = btn.get_attribute('onclick') or ''
                    if 'speedGoSend' in btn_onclick:
                        speedgo_button = btn
                        print("✓ 스피드고전송 버튼 찾음 (class='button2')")
                        break
            except Exception as e:
                print(f"  클래스 검색 중 오류: {e}")
        
        if not speedgo_button:
            print("✗ 스피드고전송 버튼을 찾을 수 없습니다.")
            # 디버깅: 모든 버튼 출력
            try:
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                print(f"  페이지의 모든 버튼 ({len(all_buttons)}개):")
                for i, btn in enumerate(all_buttons[:10], 1):
                    print(f"    {i}. 텍스트: '{btn.text.strip()}', onclick: '{btn.get_attribute('onclick') or ''}'")
            except:
                pass
            return False
        
        # 버튼 정보 출력
        button_text = speedgo_button.text.strip()
        button_onclick = speedgo_button.get_attribute('onclick') or ''
        print(f"  버튼 텍스트: '{button_text}'")
        print(f"  onclick 속성: '{button_onclick}'")
        
        # 버튼이 보이도록 스크롤
        print("\n스피드고전송 버튼 클릭 시도...")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", speedgo_button)
        time.sleep(0.5)
        
        # 버튼 클릭
        clicked = False
        
        # 방법 1: 직접 클릭
        try:
            speedgo_button.click()
            clicked = True
            print("✓ 스피드고전송 버튼 클릭 (직접 클릭)")
        except Exception as e:
            print(f"  직접 클릭 실패: {e}")
        
        # 방법 2: JavaScript로 클릭
        if not clicked:
            try:
                driver.execute_script("arguments[0].click();", speedgo_button)
                clicked = True
                print("✓ 스피드고전송 버튼 클릭 (JavaScript)")
            except Exception as e:
                print(f"  JavaScript 클릭 실패: {e}")
        
        # 방법 3: onclick 함수 직접 실행
        if not clicked:
            try:
                if button_onclick:
                    driver.execute_script(button_onclick)
                    clicked = True
                    print("✓ 스피드고전송 버튼 클릭 (onclick 함수 직접 실행)")
            except Exception as e:
                print(f"  onclick 함수 실행 실패: {e}")
        
        if not clicked:
            print("✗ 스피드고전송 버튼 클릭 실패")
            return False
        
        # 처리 완료 대기 (팝업 창이 뜰 때까지 대기)
        print("\n스피드고전송 팝업 창 대기 중...")
        time.sleep(2)
        
        # 팝업 창이 나타날 때까지 대기
        popup_loaded = False
        
        # CSS 선택자로 팝업 확인 (표준 CSS만 사용)
        css_selectors = [
            "div[style*='background:#2c303b']",
            "#mkForm",
            "div.pup_images_tit",
        ]
        
        for selector in css_selectors:
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                popup_loaded = True
                print(f"✓ 팝업 창 로드 확인: {selector}")
                break
            except TimeoutException:
                continue
        
        # XPath로 텍스트 확인
        if not popup_loaded:
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '스피드고 전송정보설정')]"))
                )
                popup_loaded = True
                print("✓ 팝업 창 로드 확인 (XPath 텍스트 검색)")
            except:
                pass
        
        # 추가 확인: mkForm 요소 확인
        if not popup_loaded:
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "mkForm"))
                )
                popup_loaded = True
                print("✓ 팝업 창 로드 확인 (mkForm ID)")
            except:
                pass
        
        if popup_loaded:
            time.sleep(1)
            print("✓ 팝업 창이 열렸습니다.")
        else:
            print("⚠ 팝업 창이 감지되지 않았지만 계속 진행합니다...")
        
        # iframe으로 전환 (팝업 내부에 iframe이 있을 수 있음)
        iframe_switched = False
        try:
            # iframe 찾기 (여러 방법 시도)
            iframe_selectors = [
                "iframe[id*='layui-layer-iframe']",
                "iframe[name*='layui-layer-iframe']",
                "iframe[src*='popup_setBulkProduct']",
                "iframe"
            ]
            
            for selector in iframe_selectors:
                try:
                    iframes = driver.find_elements(By.CSS_SELECTOR, selector)
                    for iframe in iframes:
                        iframe_src = iframe.get_attribute('src') or ''
                        if 'popup_setBulkProduct' in iframe_src or 'layui-layer-iframe' in (iframe.get_attribute('id') or ''):
                            print(f"✓ iframe 발견: {iframe.get_attribute('id')} (src: {iframe_src[:80]}...)")
                            driver.switch_to.frame(iframe)
                            iframe_switched = True
                            print("✓ iframe으로 전환 완료")
                            time.sleep(1)  # iframe 내부 로딩 대기
                            break
                    if iframe_switched:
                        break
                except Exception as e:
                    continue
        except Exception as e:
            print(f"  iframe 전환 시도 중 오류 (계속 진행): {e}")
        
        # 팝업 창 내부에서 두 번째 스피드고전송 버튼 찾기
        print("\n팝업 창 내부에서 두 번째 스피드고전송 버튼 찾는 중...")
        speedgo_button2 = None
        
        # 방법 1: 제공된 XPath 선택자 사용 (가장 정확)
        try:
            speedgo_button2 = driver.find_element(By.XPATH, "//*[@id='mkForm']/div/div[3]/div[11]/button[1]")
            print("✓ 두 번째 스피드고전송 버튼 찾음 (제공된 XPath 선택자)")
        except NoSuchElementException:
            # 방법 2: CSS 선택자로 시도
            try:
                speedgo_button2 = driver.find_element(By.CSS_SELECTOR, "#mkForm > div > div.fr > div.cb.t50 > button:nth-child(1)")
                print("✓ 두 번째 스피드고전송 버튼 찾음 (CSS 선택자)")
            except NoSuchElementException:
                # 방법 3: 더 간단한 선택자 시도
                try:
                    speedgo_button2 = driver.find_element(By.CSS_SELECTOR, "#mkForm button")
                    print("✓ 두 번째 스피드고전송 버튼 찾음 (#mkForm button)")
                except:
                    # 방법 4: onclick="goProduct()" 속성으로 찾기
                    try:
                        buttons = driver.find_elements(By.CSS_SELECTOR, "button[onclick*='goProduct']")
                        for btn in buttons:
                            onclick_attr = btn.get_attribute('onclick') or ''
                            if 'goProduct' in onclick_attr:
                                speedgo_button2 = btn
                                print("✓ 두 번째 스피드고전송 버튼 찾음 (onclick='goProduct')")
                                break
                    except Exception as e:
                        print(f"  onclick 검색 중 오류: {e}")
        
        # 방법 4: 텍스트와 onclick 조합으로 찾기
        if not speedgo_button2:
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    btn_text = btn.text.strip()
                    btn_onclick = btn.get_attribute('onclick') or ''
                    if ("스피드고전송" in btn_text or "스피드고" in btn_text) and "goProduct" in btn_onclick:
                        speedgo_button2 = btn
                        print("✓ 두 번째 스피드고전송 버튼 찾음 (텍스트 + onclick 검색)")
                        break
            except Exception as e:
                print(f"  텍스트 검색 중 오류: {e}")
        
        # 방법 5: 클래스로 찾기
        if not speedgo_button2:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, "button.cont_btn1")
                for btn in buttons:
                    btn_onclick = btn.get_attribute('onclick') or ''
                    btn_text = btn.text.strip()
                    if 'goProduct' in btn_onclick:
                        speedgo_button2 = btn
                        print("✓ 두 번째 스피드고전송 버튼 찾음 (class='cont_btn1')")
                        break
            except Exception as e:
                print(f"  클래스 검색 중 오류: {e}")
        
        if not speedgo_button2:
            print("✗ 두 번째 스피드고전송 버튼을 찾을 수 없습니다.")
            # 디버깅: 팝업 창 내부의 모든 버튼 출력
            try:
                # mkForm 내부의 버튼만 찾기
                mkform = driver.find_element(By.ID, "mkForm")
                all_buttons = mkform.find_elements(By.TAG_NAME, "button")
                print(f"  팝업 창 내부의 모든 버튼 ({len(all_buttons)}개):")
                for i, btn in enumerate(all_buttons[:15], 1):
                    btn_text = btn.text.strip()
                    btn_onclick = btn.get_attribute('onclick') or ''
                    print(f"    {i}. 텍스트: '{btn_text}', onclick: '{btn_onclick}'")
            except:
                # 전체 페이지의 버튼 출력
                try:
                    all_buttons = driver.find_elements(By.TAG_NAME, "button")
                    print(f"  페이지의 모든 버튼 ({len(all_buttons)}개):")
                    for i, btn in enumerate(all_buttons[:15], 1):
                        btn_text = btn.text.strip()
                        btn_onclick = btn.get_attribute('onclick') or ''
                        print(f"    {i}. 텍스트: '{btn_text}', onclick: '{btn_onclick}'")
                except:
                    pass
            return False
        
        # 버튼 정보 출력
        button_text2 = speedgo_button2.text.strip()
        button_onclick2 = speedgo_button2.get_attribute('onclick') or ''
        print(f"  버튼 텍스트: '{button_text2}'")
        print(f"  onclick 속성: '{button_onclick2}'")
        
        # 버튼이 보이도록 스크롤
        print("\n두 번째 스피드고전송 버튼 클릭 시도...")
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", speedgo_button2)
            time.sleep(0.5)
        except:
            pass
        
        # 버튼 클릭
        clicked2 = False
        
        # 방법 1: 직접 클릭
        try:
            speedgo_button2.click()
            clicked2 = True
            print("✓ 두 번째 스피드고전송 버튼 클릭 (직접 클릭)")
        except Exception as e:
            print(f"  직접 클릭 실패: {e}")
        
        # 방법 2: JavaScript로 클릭
        if not clicked2:
            try:
                driver.execute_script("arguments[0].click();", speedgo_button2)
                clicked2 = True
                print("✓ 두 번째 스피드고전송 버튼 클릭 (JavaScript)")
            except Exception as e:
                print(f"  JavaScript 클릭 실패: {e}")
        
        # 방법 3: onclick 함수 직접 실행
        if not clicked2:
            try:
                if button_onclick2:
                    driver.execute_script(button_onclick2)
                    clicked2 = True
                    print("✓ 두 번째 스피드고전송 버튼 클릭 (onclick 함수 직접 실행)")
            except Exception as e:
                print(f"  onclick 함수 실행 실패: {e}")
        
        if not clicked2:
            print("✗ 두 번째 스피드고전송 버튼 클릭 실패")
            return False
        
        # 처리 완료 대기
        print("\n두 번째 스피드고전송 처리 대기 중...")
        time.sleep(3)
        
        # iframe에서 나오기 (기본 컨텍스트로 복귀)
        if iframe_switched:
            try:
                driver.switch_to.default_content()
                print("✓ 기본 컨텍스트로 복귀")
            except:
                pass
        
        print("✓ 스피드고전송 완료!")
        return True
        
    except Exception as e:
        # 예외 발생 시에도 iframe에서 나오기
        try:
            driver.switch_to.default_content()
        except:
            pass
        print(f"✗ 마이박스담기 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def search_products(search_keyword, headless=True, max_results=None, use_direct_url=False, min_price=None, username=None, password=None, return_driver=False):
    """
    도매꾹 사이트에서 상품 검색
    
    Args:
        search_keyword: 검색할 키워드
        headless: 헤드리스 모드 사용 여부
        max_results: 가져올 최대 결과 수 (None이면 모두 가져옴)
        use_direct_url: True면 검색 폼 대신 직접 URL로 접근
        min_price: 최소 가격 (이 가격 이상인 상품만 필터링, 예: 12000)
        username: 로그인 아이디 (None이면 사용자 입력 요청)
        password: 비밀번호 (None이면 사용자 입력 요청)
    
    Returns:
        검색 결과 리스트 (딕셔너리 형태)
    """
    driver = None
    
    # 직접 URL 접근 방식
    if use_direct_url:
        try:
            print(f"\n검색어 '{search_keyword}'로 직접 URL 접근...")
            # URL 인코딩
            encoded_keyword = quote(search_keyword, safe='')
            search_url = f"https://domemedb.domeggook.com/index/item/supplyList.php?sf=subject&enc=utf8&fromOversea=0&mode=search&sw={encoded_keyword}"
            
            driver = get_chrome_driver(headless=headless)
            
            # 먼저 로그인
            if not login_to_domeggook(driver, username=username, password=password):
                print("✗ 로그인 실패로 검색을 중단합니다.")
                if driver:
                    driver.quit()
                return []
            
            # 검색 페이지로 이동
            driver.get(search_url)
            print(f"✓ 검색 URL로 직접 접근: {search_url}")
            
            # 페이지 로딩 대기
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 검색 결과 요소가 로드될 때까지 대기
            try:
                # 여러 선택자를 순차적으로 시도
                result_loaded = False
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
                        print(f"✓ 검색 결과 요소 로드 완료: {selector}")
                        result_loaded = True
                        break
                    except TimeoutException:
                        continue
                if not result_loaded:
                    print("⚠ 검색 결과 요소를 찾지 못했지만 계속 진행합니다...")
            except Exception as e:
                print(f"⚠ 검색 결과 요소 대기 중 오류: {e}")
            
            # 페이지 스크롤하여 동적 콘텐츠 로드
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            except:
                pass
            
            time.sleep(2)
            
            # 검색 결과 파싱
            results = parse_search_results(driver, max_results, min_price=min_price)
            if min_price:
                print(f"\n✓ 검색 완료! {min_price:,}원 이상 상품 {len(results)}개 발견")
            else:
                print(f"\n✓ 검색 완료! 총 {len(results)}개 결과 발견")
            
            if return_driver:
                return results, driver
            return results
            
        except Exception as e:
            print(f"✗ 직접 URL 접근 실패: {e}")
            import traceback
            traceback.print_exc()
            if return_driver:
                return [], driver if driver else None
            if driver:
                driver.quit()
            return []
    
    # 검색 폼 사용 방식 (기존 방식)
    url = "https://domemedb.domeggook.com/index/?mainChannel=aihome"
    
    try:
        print(f"\n검색어 '{search_keyword}'로 검색 시작...")
        driver = get_chrome_driver(headless=headless)
        
        # 먼저 로그인
        if not login_to_domeggook(driver, username=username, password=password):
            print("✗ 로그인 실패로 검색을 중단합니다.")
            if driver:
                driver.quit()
            return []
        
        # 메인 페이지로 이동
        driver.get(url)
        
        # 페이지 로딩 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)  # 추가 로딩 대기
        
        # 검색창 찾기 (여러 가능한 선택자 시도)
        # name="sw"가 가장 정확한 선택자이므로 우선 시도
        search_selectors = [
            "input[name='sw']",  # 정확한 name 속성으로 검색
            "input[type='text'][name='sw']",  # type과 name 조합
            "input[title='검색'][name='sw']",  # title과 name 조합
            "input[type='text'][name*='search']",
            "input[type='text'][id*='search']",
            "input[type='text'][class*='search']",
            "input[placeholder*='상품명']",
            "input[placeholder*='검색']",
            "#searchKeyword",
            ".search-input",
            "input.form-control",
        ]
        
        search_input = None
        for selector in search_selectors:
            try:
                search_input = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                print(f"✓ 검색창 찾음: {selector}")
                break
            except TimeoutException:
                continue
        
        if not search_input:
            # name 속성으로 직접 찾기 시도
            try:
                search_input = driver.find_element(By.NAME, "sw")
                print("✓ 검색창 찾음: name='sw'")
            except NoSuchElementException:
                pass
        
        if not search_input:
            # 모든 input 요소 확인
            inputs = driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                inp_name = inp.get_attribute("name") or ""
                inp_type = inp.get_attribute("type")
                inp_title = inp.get_attribute("title") or ""
                if inp_name == "sw" or (inp_type == "text" and "검색" in inp_title):
                    search_input = inp
                    print(f"✓ 검색창 찾음 (name={inp_name}, title={inp_title})")
                    break
        
        if not search_input:
            raise Exception("검색창을 찾을 수 없습니다.")
        
        # 검색어 입력
        search_input.clear()
        search_input.send_keys(search_keyword)
        time.sleep(0.5)
        
        # 검색 버튼 찾기 및 클릭 또는 Enter 키 입력
        search_button_selectors = [
            "button[type='submit']",
            "button.btn-search",
            "button[class*='search']",
            "input[type='submit']",
            ".search-btn",
            "#searchBtn",
        ]
        
        search_button = None
        for selector in search_button_selectors:
            try:
                search_button = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"✓ 검색 버튼 찾음: {selector}")
                break
            except NoSuchElementException:
                continue
        
        # 현재 URL 저장 (검색 전)
        initial_url = driver.current_url
        print(f"검색 전 URL: {initial_url}")
        
        if search_button:
            search_button.click()
        else:
            # 검색 버튼을 찾지 못하면 Enter 키 입력
            search_input.send_keys(Keys.RETURN)
            print("✓ Enter 키로 검색 실행")
        
        # 검색 결과 페이지 로딩 대기
        print("검색 결과 페이지 로딩 대기 중...")
        
        # URL 변경 확인 (supplyList.php로 이동하는지 확인)
        try:
            # URL이 변경되고 supplyList.php를 포함하는지 확인
            WebDriverWait(driver, 15).until(
                lambda d: (
                    "supplyList.php" in d.current_url or 
                    "search" in d.current_url.lower() or
                    d.current_url != initial_url
                )
            )
            print(f"✓ 검색 결과 페이지로 이동: {driver.current_url}")
            
            # URL에서 검색어 확인
            parsed_url = urlparse(driver.current_url)
            query_params = parse_qs(parsed_url.query)
            if 'sw' in query_params:
                decoded_keyword = query_params['sw'][0]
                print(f"✓ URL에서 검색어 확인: {decoded_keyword}")
            
        except TimeoutException:
            print("⚠ URL 변경이 감지되지 않았지만 계속 진행합니다...")
        
        # 검색 결과 요소가 로드될 때까지 대기
        try:
            # 여러 선택자를 순차적으로 시도
            result_loaded = False
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
                    print(f"✓ 검색 결과 요소 로드 완료: {selector}")
                    result_loaded = True
                    break
                except TimeoutException:
                    continue
            if not result_loaded:
                print("⚠ 검색 결과 요소를 찾지 못했지만 계속 진행합니다...")
        except Exception as e:
            print(f"⚠ 검색 결과 요소 대기 중 오류: {e}")
        
        # 페이지 스크롤하여 동적 콘텐츠 로드
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
        except:
            pass
        
        # 추가 로딩 대기 (동적 콘텐츠 로딩)
        time.sleep(2)
        
        # 검색 결과 파싱
        results = parse_search_results(driver, max_results, min_price=min_price)
        
        if min_price:
            print(f"\n✓ 검색 완료! {min_price:,}원 이상 상품 {len(results)}개 발견")
        else:
            print(f"\n✓ 검색 완료! 총 {len(results)}개 결과 발견")
        
        if return_driver:
            return results, driver
        return results
        
    except Exception as e:
        print(f"✗ 검색 실패: {e}")
        import traceback
        traceback.print_exc()
        if return_driver:
            return [], driver if driver else None
        if driver and not return_driver:
            driver.quit()
        return []


def extract_price_number(price_text):
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


def parse_search_results(driver, max_results=None, min_price=None):
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
        # 도매꾹 사이트의 실제 상품 컨테이너 선택자
        product_selectors = [
            ".sub_cont_bane1",  # 메인 상품 컨테이너
            ".sub_cont_bane1_SetListGallery",  # 갤러리 뷰 상품 컨테이너
        ]
        
        products = []
        for selector in product_selectors:
            try:
                products = driver.find_elements(By.CSS_SELECTOR, selector)
                if len(products) > 0:
                    print(f"✓ 상품 요소 찾음: {selector} ({len(products)}개)")
                    break
            except:
                continue
        
        if not products:
            # 페이지 소스를 확인하여 구조 파악
            print("상품 요소를 찾지 못했습니다. 페이지 구조 확인 중...")
            page_source = driver.page_source[:5000]  # 처음 5000자만 확인
            print(f"페이지 소스 샘플:\n{page_source}")
            return results
        
        # 각 상품 정보 추출
        product_list = products[:max_results] if max_results else products
        for idx, product in enumerate(product_list):
            try:
                product_info = {}
                
                # 상품번호 추출 (우선순위: input value > span.txt8)
                product_id = None
                try:
                    # checkbox의 value 속성에서 상품번호 추출
                    checkbox = product.find_element(By.CSS_SELECTOR, "input[name='item[]']")
                    product_id = checkbox.get_attribute('value')
                except:
                    pass
                
                if not product_id:
                    # span.txt8에서 상품번호 추출
                    try:
                        product_id_elems = product.find_elements(By.CSS_SELECTOR, "span.txt8")
                        for elem in product_id_elems:
                            text = elem.text.strip()
                            if text.isdigit() and len(text) >= 6:  # 상품번호는 보통 6자리 이상
                                product_id = text
                                break
                    except:
                        pass
                
                product_info['product_id'] = product_id or ''
                
                # 상품명 추출 (.itemName 클래스)
                try:
                    name_elem = product.find_element(By.CSS_SELECTOR, ".itemName")
                    product_info['name'] = name_elem.text.strip()
                except:
                    # 백업: main_cont_text1에서 추출
                    try:
                        name_elem = product.find_element(By.CSS_SELECTOR, ".main_cont_text1.b")
                        product_info['name'] = name_elem.text.strip()
                    except:
                        product_info['name'] = ''
                
                # 가격 추출: <div class="main_cont_text1 priceLg"><strong>29,530</strong> 원</div>
                price_value = None
                price_display = ''
                
                # 다양한 선택자 시도
                price_selectors = [
                    (".main_cont_text1.priceLg strong", "방법1: .main_cont_text1.priceLg strong"),
                    (".priceLg strong", "방법2: .priceLg strong"),
                    (".main_cont_text1.priceLg", "방법3: .main_cont_text1.priceLg (전체)"),
                    (".priceLg", "방법4: .priceLg (전체)"),
                ]
                
                for selector, method_name in price_selectors:
                    try:
                        if "strong" in selector:
                            # strong 태그 직접 찾기
                            price_elem = product.find_element(By.CSS_SELECTOR, selector)
                            price_text = price_elem.text.strip()
                        else:
                            # 컨테이너에서 strong 태그 찾기
                            price_container = product.find_element(By.CSS_SELECTOR, selector)
                            try:
                                price_elem = price_container.find_element(By.CSS_SELECTOR, "strong")
                                price_text = price_elem.text.strip()
                            except:
                                # strong 태그가 없으면 전체 텍스트 사용
                                price_text = price_container.text.strip()
                        
                        if price_text:
                            price_value = extract_price_number(price_text)
                            if price_value is not None and price_value >= 100:  # 최소 100원 이상
                                price_display = f"{price_value:,}원"
                                break
                    except (NoSuchElementException, Exception):
                        continue
                
                # 위 방법들이 모두 실패하면 모든 strong 태그에서 찾기
                if price_value is None:
                    try:
                        strong_elems = product.find_elements(By.CSS_SELECTOR, "strong")
                        for strong in strong_elems:
                            text = strong.text.strip()
                            if not text:
                                continue
                            temp_value = extract_price_number(text)
                            # 가격은 보통 100원 이상이고, 너무 큰 숫자(등급 등)는 제외
                            if temp_value is not None and 100 <= temp_value <= 10000000:
                                price_value = temp_value
                                price_display = f"{price_value:,}원"
                                break
                    except Exception as e:
                        pass
                
                # 가격 정보 저장
                product_info['price'] = price_display  # 표시용 문자열 (예: "29,530원")
                product_info['price_value'] = price_value  # 정수 값 (예: 29530) - 필터링용
                
                # 디버깅: 가격을 찾지 못한 경우 상세 정보 출력
                if price_value is None:
                    try:
                        # 모든 priceLg 요소 찾기 시도
                        price_containers = product.find_elements(By.CSS_SELECTOR, ".priceLg, .main_cont_text1.priceLg")
                        if price_containers:
                            for i, container in enumerate(price_containers):
                                container_text = container.text.strip()
                                print(f"상품 {idx+1} 디버깅: priceLg 요소 {i+1} 발견 - 텍스트: '{container_text}'")
                        else:
                            # 상품의 일부 HTML을 확인 (디버깅용)
                            product_html = product.get_attribute('outerHTML')[:800]
                            print(f"상품 {idx+1} 디버깅: priceLg 요소를 찾지 못함")
                            print(f"  HTML 샘플: {product_html[:400]}...")
                    except Exception as e:
                        print(f"상품 {idx+1} 디버깅 중 오류: {e}")
                
                # 이미지 추출 (.bane_brd1 img)
                try:
                    img_elem = product.find_element(By.CSS_SELECTOR, ".bane_brd1 img")
                    product_info['image'] = img_elem.get_attribute('src') or img_elem.get_attribute('data-src') or ''
                except:
                    # 백업: 모든 img 태그에서 상품 이미지 찾기
                    try:
                        imgs = product.find_elements(By.CSS_SELECTOR, "img")
                        for img in imgs:
                            src = img.get_attribute('src') or ''
                            if 'domeggook.com' in src and 'upload/item' in src:
                                product_info['image'] = src
                                break
                    except:
                        product_info['image'] = ''
                
                # 판매자 정보 추출
                try:
                    seller_elem = product.find_element(By.CSS_SELECTOR, "a[onclick*='supplyList']")
                    seller_text = seller_elem.text.strip()
                    product_info['seller'] = seller_text
                except:
                    product_info['seller'] = ''
                
                # 상품 상세 링크 생성 (onclick에서 상품번호 추출)
                if product_id:
                    product_info['link'] = f"https://domemedb.domeggook.com/index/item/itemView.php?itemNo={product_id}"
                else:
                    product_info['link'] = ''
                
                # 추가 정보: 등급 추출
                try:
                    # 등급이 표시된 부분 찾기 (strong 태그 주변에 "등급" 텍스트가 있는 경우)
                    grade_elems = product.find_elements(By.CSS_SELECTOR, ".main_cont_text3")
                    for elem in grade_elems:
                        text = elem.text.strip()
                        if '등급' in text:
                            # strong 태그에서 숫자 추출
                            try:
                                strong = elem.find_element(By.CSS_SELECTOR, "strong")
                                product_info['grade'] = strong.text.strip()
                                break
                            except:
                                # strong 태그가 없으면 텍스트에서 숫자 추출
                                match = re.search(r'(\d+)등급', text)
                                if match:
                                    product_info['grade'] = match.group(1)
                                    break
                except:
                    product_info['grade'] = ''
                
                # 빠른배송 여부
                try:
                    fast_delivery = product.find_element(By.CSS_SELECTOR, ".main_cont_bu9")
                    product_info['fast_delivery'] = True
                except:
                    product_info['fast_delivery'] = False
                
                # 가격 필터링 적용
                if min_price is not None:
                    if product_info.get('price_value') is None:
                        print(f"상품 {idx+1}: 가격을 파싱할 수 없어 건너뜀")
                        continue
                    if product_info['price_value'] < min_price:
                        print(f"상품 {idx+1}: 가격 {product_info.get('price', 'N/A')}이(가) 최소 가격 {min_price:,}원 미만이어서 건너뜀")
                        continue
                
                # 상품명이 있으면 결과에 추가
                if product_info.get('name'):
                    results.append(product_info)
                else:
                    print(f"상품 {idx+1}: 상품명을 찾을 수 없어 건너뜀")
                    
            except Exception as e:
                print(f"상품 {idx+1} 파싱 중 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
    except Exception as e:
        print(f"결과 파싱 중 오류: {e}")
        import traceback
        traceback.print_exc()
    
    return results


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("도매꾹 사이트 검색 도구")
    print("=" * 60)
    print()
    
    # 명령줄 인자로 검색어 받기 (여러 개 가능: 쉼표 또는 공백으로 구분)
    if len(sys.argv) > 1:
        # 명령줄 인자들을 합쳐서 처리 (공백으로 구분된 여러 검색어)
        search_keywords_input = " ".join(sys.argv[1:])
    else:
        # 기본 검색어 또는 사용자 입력
        search_keywords_input = input("검색할 상품명을 입력하세요 (여러 개는 쉼표 또는 공백으로 구분): ").strip()
        if not search_keywords_input:
            search_keywords_input = "양말"  # 기본값
    
    # 검색어 분리 (쉼표 또는 공백으로 구분)
    search_keywords = []
    if ',' in search_keywords_input:
        # 쉼표로 구분
        search_keywords = [kw.strip() for kw in search_keywords_input.split(',') if kw.strip()]
    else:
        # 공백으로 구분 (하지만 하나의 검색어일 수도 있음)
        # 사용자가 여러 단어로 된 하나의 검색어를 입력했을 수도 있으므로
        # 일단 하나로 처리하고, 명령줄 인자로 여러 개가 들어온 경우만 분리
        if len(sys.argv) > 2:
            # 명령줄에서 여러 개가 들어온 경우
            search_keywords = [kw.strip() for kw in sys.argv[1:] if kw.strip()]
        else:
            # 하나의 검색어로 처리
            search_keywords = [search_keywords_input]
    
    # 검색어가 없으면 기본값 사용
    if not search_keywords:
        search_keywords = ["양말"]
    
    print(f"\n총 {len(search_keywords)}개의 검색어를 처리합니다:")
    for idx, kw in enumerate(search_keywords, 1):
        print(f"  {idx}. {kw}")
    print()
    
    # 직접 URL 접근 방식 사용 (더 빠르고 안정적)
    # use_direct_url=True로 설정하면 검색 폼 대신 직접 URL로 접근
    # min_price=12000으로 설정하면 12,000원 이상인 상품만 필터링
    # 
    # 로그인 정보 설정:
    # - 아래에 직접 아이디와 비밀번호를 입력하거나
    # - None으로 두면 실행 시 입력 요청 또는 환경변수(DOMEID, DOMPWD) 사용
    # - 보안을 위해 환경변수 사용을 권장합니다
    MY_USERNAME = None  # 여기에 아이디를 입력하세요 (예: "your_id")
    MY_PASSWORD = None  # 여기에 비밀번호를 입력하세요 (예: "your_password")
    
    # driver는 한 번만 생성하고 재사용
    driver = None
    
    # result 폴더 생성 (없으면 생성)
    result_dir = "result"
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
        print(f"✓ '{result_dir}' 폴더를 생성했습니다.")
    
    try:
        # 각 검색어마다 순차 처리
        for search_idx, search_keyword in enumerate(search_keywords, 1):
            print("\n" + "=" * 60)
            print(f"[{search_idx}/{len(search_keywords)}] 검색어: '{search_keyword}'")
            print("=" * 60)
            
            # 첫 번째 검색어일 때만 driver 생성 (로그인 포함)
            if driver is None:
                # 검색 실행 (driver도 함께 반환받기 위해 return_driver=True)
                search_result = search_products(
                    search_keyword, 
                    headless=False,  # 로그인을 위해 브라우저 창 표시 (필요시 True로 변경)
                    max_results=20, 
                    use_direct_url=True,
                    min_price=12000,  # 12,000원 이상인 상품만 필터링
                    username=MY_USERNAME,  # 직접 입력하거나 None으로 두면 실행 시 입력 요청
                    password=MY_PASSWORD,   # 직접 입력하거나 None으로 두면 실행 시 입력 요청
                    return_driver=True  # driver도 함께 반환받기
                )
                
                # 결과와 driver 분리
                if isinstance(search_result, tuple):
                    results, driver = search_result
                else:
                    results = search_result
                    driver = None
            else:
                # 두 번째 검색어부터는 기존 driver 재사용 (이미 로그인됨)
                # 검색 페이지만 이동
                encoded_keyword = quote(search_keyword, safe='')
                search_url = f"https://domemedb.domeggook.com/index/item/supplyList.php?sf=subject&enc=utf8&fromOversea=0&mode=search&sw={encoded_keyword}"
                driver.get(search_url)
                print(f"✓ 검색 URL로 이동: {search_url}")
                
                # 페이지 로딩 대기
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # 검색 결과 파싱
                time.sleep(2)  # 동적 콘텐츠 로딩 대기
                results = parse_search_results(driver, max_results=20, min_price=12000)
            
            # 결과 출력
            if results:
                print(f"\n검색 결과: {len(results)}개 상품 발견")
                
                for idx, product in enumerate(results, 1):
                    print(f"\n[{idx}] {product.get('name', 'N/A')}")
                    if product.get('product_id'):
                        print(f"    상품번호: {product['product_id']}")
                    if product.get('price'):
                        print(f"    가격: {product['price']}")
                    if product.get('seller'):
                        print(f"    판매자: {product['seller']}")
                    if product.get('grade'):
                        print(f"    등급: {product['grade']}등급")
                    if product.get('fast_delivery'):
                        print(f"    빠른배송: 가능")
                
                # JSON 파일로 저장 (result 폴더에 저장)
                safe_keyword = search_keyword.replace(' ', '_').replace('/', '_')
                output_file = os.path.join(result_dir, f"search_results_{safe_keyword}.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"\n✓ 결과가 '{output_file}' 파일에 저장되었습니다.")
                
                # 마이박스에 상품 추가 및 스피드고 전송 (driver가 있는 경우)
                if driver:
                    # 검색 결과에서 상품번호 추출
                    product_ids = [p.get('product_id') for p in results if p.get('product_id')]
                    
                    if product_ids:
                        print(f"\n{'=' * 60}")
                        print(f"마이박스에 {len(product_ids)}개 상품 추가 및 스피드고 전송 시도")
                        print(f"{'=' * 60}")
                        
                        # 마이박스담기 및 스피드고 전송 실행
                        success = add_products_to_mybox(driver, product_ids=product_ids, select_all=False)
                        
                        if success:
                            print(f"\n✓ 검색어 '{search_keyword}' 처리 완료!")
                        else:
                            print(f"\n✗ 검색어 '{search_keyword}' 처리 실패")
                    else:
                        print(f"\n⚠ 검색어 '{search_keyword}': 상품번호를 찾을 수 없어 마이박스담기를 건너뜁니다.")
                else:
                    print(f"\n⚠ 검색어 '{search_keyword}': driver가 없어 마이박스담기를 건너뜁니다.")
            else:
                print(f"\n검색어 '{search_keyword}': 검색 결과가 없습니다.")
            
            # 다음 검색어 처리 전 잠시 대기
            if search_idx < len(search_keywords):
                print(f"\n다음 검색어로 이동합니다...")
                time.sleep(2)
    
    finally:
        # driver 종료
        if driver:
            print("\n브라우저를 종료합니다...")
            driver.quit()
    
    print("\n" + "=" * 60)
    print("모든 검색어 처리 완료!")
    print("=" * 60)

