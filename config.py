"""
도매꾹 스크래핑 프로젝트 설정 파일
"""
import os
from typing import Optional

# 기본 URL 설정
BASE_URL = "https://domemedb.domeggook.com/index/?mainChannel=aihome"
LOGIN_URL_BASE = "https://domeggook.com/ssl/member/mem_loginForm.php"
SPEEDGO_URL = "https://speedgo.domeggook.com/"
MYBOX_URL = "https://speedgo.domeggook.com/mybox/mb_saveList.php"

# 로그인 관련 설정
LOGIN_BACK_URL_BASE64 = "aHR0cHM6Ly9kb21lbWVkYi5kb21lZ2dvb2suY29tL2luZGV4"

# 검색 관련 설정
SEARCH_URL_TEMPLATE = "https://domemedb.domeggook.com/index/item/supplyList.php?sf=subject&enc=utf8&fromOversea=0&mode=search&sw={keyword}"
SEARCH_URL_TEMPLATE_WITH_PAGE = "https://domemedb.domeggook.com/index/item/supplyList.php?sf=subject&enc=utf8&fromOversea=0&mode=search&sw={keyword}&page={page}"

# Selenium 설정
DEFAULT_HEADLESS = True
DEFAULT_TIMEOUT = 10
PAGE_LOAD_TIMEOUT = 15

# User-Agent 설정 (최신 Chrome 버전)
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

# Chrome 옵션 설정
CHROME_OPTIONS = [
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-blink-features=AutomationControlled',
]

# 대기 시간 설정 (초)
WAIT_TIMES = {
    'page_load': 2,
    'element': 0.5,
    'click': 0.3,
    'scroll': 0.1,
    'iframe': 1,
    'popup': 2,
    'action_complete': 3,
}

# CSS 선택자 설정
SELECTORS = {
    # 로그인 관련
    'login': {
        'user_id': [
            "input[name='user_id']",
            "input[name='id']",
            "input[name='username']",
            "input[name='mem_id']",
            "#user_id",
            "#id",
            "#mem_id",
        ],
        'password': [
            "input[name='password']",
            "input[name='pwd']",
            "input[type='password']",
            "#password",
            "#pwd",
        ],
        'login_button': [
            "button[type='submit']",
            "input[type='submit']",
            "button.btn-login",
            "#loginBtn",
        ],
    },
    # 검색 관련
    'search': {
        'search_input': [
            "input[name='sw']",
            "input[type='text'][name='sw']",
            "#searchKeyword",
        ],
        'search_button': [
            "button[type='submit']",
            "button.btn-search",
            "#searchBtn",
        ],
        # 페이지네이션 관련
        'pagination': {
            'next_page': [
                "a[onclick*='next']",
                "a:contains('다음')",
                ".pagination a.next",
                "a.paging_next",
                "a[href*='page=']",
            ],
            'page_numbers': [
                ".pagination a",
                ".paging a",
                "a[href*='page=']",
            ],
            'current_page': [
                ".pagination .active",
                ".paging .current",
                "a[class*='current']",
            ],
        },
    },
    # 상품 관련
    'product': {
        'container': [
            ".sub_cont_bane1",
            ".sub_cont_bane1_SetListGallery",
        ],
        'checkbox': "input[name='item[]']",
        'name': ".itemName",
        'price': [
            ".main_cont_text1.priceLg strong",
            ".priceLg strong",
        ],
        'image': ".bane_brd1 img",
        'seller': "a[onclick*='supplyList']",
    },
    # 마이박스 관련
    'mybox': {
        'add_button': "button[onclick*='hashTagAdd']",
        'select_all': "#selectAll",
        'speedgo_button': "button[onclick*='speedGoSend']",
        'speedgo_button2': "button[onclick*='goProduct']",
        'link': "a[href*='mybox/mb_saveList.php']",
    },
}

# 환경변수에서 로그인 정보 읽기
def get_username() -> Optional[str]:
    """환경변수에서 사용자명 읽기"""
    return os.getenv('DOMEID')

def get_password() -> Optional[str]:
    """환경변수에서 비밀번호 읽기"""
    return os.getenv('DOMPWD')

# 결과 저장 경로
RESULT_DIR = "result"

# 기본 검색 설정
DEFAULT_MAX_RESULTS = 20
DEFAULT_MIN_PRICE = 12000

# 쿠팡 쇼핑몰 URL
COUPANG_SHOPPING_URL = "https://www.coupang.com"
COUPANG_SEARCH_URL = "https://www.coupang.com/np/search?q={keyword}"

# 네이버 쇼핑 URL
NAVER_SHOPPING_URL = "https://shopping.naver.com"
NAVER_SHOPPING_SEARCH_URL = "https://search.shopping.naver.com/search/all?query={keyword}"

