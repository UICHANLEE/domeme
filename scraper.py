"""
웹 스크래핑 관련 유틸리티 모듈
"""
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from typing import Optional
import logging

from config import USER_AGENT, CHROME_OPTIONS, BASE_URL
from logger import default_logger as logger

def get_chrome_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Chrome WebDriver 설정 및 반환
    
    Args:
        headless: 헤드리스 모드 사용 여부
    
    Returns:
        Chrome WebDriver 객체
    """
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument('--headless')
    
    # 기본 옵션 추가
    for option in CHROME_OPTIONS:
        chrome_options.add_argument(option)
    
    # 봇 탐지 우회 옵션 강화
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 최신 User-Agent 사용
    chrome_options.add_argument(f'user-agent={USER_AGENT}')
    
    # 추가 봇 탐지 우회 옵션
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--allow-running-insecure-content')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--disable-default-apps')
    chrome_options.add_argument('--disable-popup-blocking')
    
    # 언어 및 지역 설정
    chrome_options.add_argument('--lang=ko-KR')
    chrome_options.add_argument('--accept-lang=ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        # JavaScript로 봇 탐지 우회
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
        
        logger.info("Chrome WebDriver 생성 성공")
        return driver
    except Exception as e:
        logger.error(f"Chrome WebDriver 생성 실패: {e}")
        raise

def access_with_requests() -> Optional[requests.Response]:
    """
    requests 라이브러리를 사용한 간단한 접속
    
    Returns:
        Response 객체 또는 None
    """
    headers = {'User-Agent': USER_AGENT}
    
    try:
        logger.info(f"requests로 {BASE_URL} 접속 시도 중...")
        response = requests.get(BASE_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        title = BeautifulSoup(response.text, 'html.parser').title.string if response.text else 'N/A'
        logger.info(f"✓ 접속 성공! 상태 코드: {response.status_code}")
        logger.info(f"✓ 페이지 제목: {title}")
        
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"✗ 접속 실패: {e}")
        return None

