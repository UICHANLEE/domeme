"""
도매꾹 사이트 검색 도구 - 메인 실행 파일
"""
import argparse
import json
import os
import sys
from typing import List, Optional
from urllib.parse import quote

from config import (
    RESULT_DIR, DEFAULT_MAX_RESULTS, DEFAULT_MIN_PRICE,
    get_username, get_password
)
from scraper import get_chrome_driver
from search import search_products
from parser import parse_search_results
from mybox import add_products_to_mybox
from logger import setup_logger, default_logger as logger

def save_results(results: List[dict], keyword: str, output_format: str = 'json') -> str:
    """
    검색 결과를 파일로 저장
    
    Args:
        results: 검색 결과 리스트
        keyword: 검색어
        output_format: 출력 형식 ('json', 'csv')
    
    Returns:
        저장된 파일 경로
    """
    # 결과 디렉토리 생성
    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)
        logger.info(f"'{RESULT_DIR}' 폴더를 생성했습니다.")
    
    # 파일명 생성 (특수문자 제거)
    safe_keyword = keyword.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    if output_format == 'json':
        output_file = os.path.join(RESULT_DIR, f"search_results_{safe_keyword}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    elif output_format == 'csv':
        import csv
        output_file = os.path.join(RESULT_DIR, f"search_results_{safe_keyword}.csv")
        if results:
            fieldnames = results[0].keys()
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
    else:
        raise ValueError(f"지원하지 않는 출력 형식: {output_format}")
    
    logger.info(f"결과가 '{output_file}' 파일에 저장되었습니다.")
    return output_file

def print_results(results: List[dict], verbose: bool = False) -> None:
    """검색 결과 출력"""
    if not results:
        logger.info("검색 결과가 없습니다.")
        return
    
    logger.info(f"\n검색 결과: {len(results)}개 상품 발견")
    
    if verbose:
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
            if product.get('link'):
                print(f"    링크: {product['link']}")
    else:
        # 간단한 요약만 출력
        for idx, product in enumerate(results[:10], 1):  # 처음 10개만
            print(f"[{idx}] {product.get('name', 'N/A')} - {product.get('price', 'N/A')}")
        if len(results) > 10:
            print(f"... 외 {len(results) - 10}개 더")

def load_keywords_from_file(file_path: str) -> List[str]:
    """파일에서 검색어 목록 읽기"""
    keywords = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):  # 빈 줄과 주석 제외
                    keywords.append(line)
        logger.info(f"파일에서 {len(keywords)}개의 검색어를 읽었습니다: {file_path}")
    except Exception as e:
        logger.error(f"파일 읽기 실패: {e}")
    return keywords

def parse_arguments():
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description='도매꾹 사이트 상품 검색 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 기본 사용 (대화형 모드 - 검색어 입력 요청)
  python main.py
  
  # 빠른 검색 (검색어를 명령줄에서 지정)
  python main.py --quick 양말
  
  # 여러 검색어 빠른 검색
  python main.py -q 양말 장갑 모자
  
  # 옵션만 지정하고 검색어는 입력받기
  python main.py --max-results 10 --min-price 15000
  
  # 파일에서 검색어 읽기
  python main.py --file keywords.txt
  
  # 빠른 검색 + 옵션
  python main.py -q 양말 --max-results 10 --min-price 15000
  
  # 마이박스에 추가하지 않고 검색만
  python main.py --no-mybox
  
  # 상세 출력
  python main.py --verbose
  
  # CSV 형식으로 저장
  python main.py --format csv
        """
    )
    
    # 검색어 관련
    parser.add_argument(
        '-q', '--quick',
        nargs='+',
        metavar='KEYWORD',
        help='빠른 검색 모드: 검색어를 명령줄에서 직접 지정 (여러 개 가능)'
    )
    parser.add_argument(
        '-f', '--file',
        type=str,
        help='검색어 목록이 있는 파일 경로 (한 줄에 하나씩)'
    )
    
    # 검색 옵션
    parser.add_argument(
        '--max-results',
        type=int,
        default=DEFAULT_MAX_RESULTS,
        help=f'가져올 최대 결과 수 (기본값: {DEFAULT_MAX_RESULTS})'
    )
    parser.add_argument(
        '--min-price',
        type=int,
        default=DEFAULT_MIN_PRICE,
        help=f'최소 가격 필터 (기본값: {DEFAULT_MIN_PRICE:,}원)'
    )
    parser.add_argument(
        '--no-price-filter',
        action='store_true',
        help='가격 필터링 비활성화'
    )
    
    # 실행 옵션
    parser.add_argument(
        '--headless',
        action='store_true',
        default=False,
        help='헤드리스 모드 (브라우저 창 숨김)'
    )
    parser.add_argument(
        '--no-mybox',
        action='store_true',
        help='마이박스에 추가하지 않고 검색만 수행'
    )
    parser.add_argument(
        '--use-form',
        action='store_true',
        help='검색 폼 사용 방식 (기본값: 직접 URL 접근)'
    )
    
    # 출력 옵션
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='상세 출력'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'csv'],
        default='json',
        help='결과 저장 형식 (기본값: json)'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='결과를 파일로 저장하지 않음'
    )
    
    # 로그인 옵션
    parser.add_argument(
        '--username',
        type=str,
        help='로그인 아이디 (기본값: 환경변수 DOMEID 또는 입력 요청)'
    )
    parser.add_argument(
        '--password',
        type=str,
        help='로그인 비밀번호 (기본값: 환경변수 DOMPWD 또는 입력 요청)'
    )
    
    # 로깅 옵션
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='로그 레벨 (기본값: INFO)'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        help='로그 파일 경로 (지정하지 않으면 파일 저장 안 함)'
    )
    
    return parser.parse_args()

def main():
    """메인 실행 함수"""
    args = parse_arguments()
    
    # 로거 설정
    log_level = getattr(__import__('logging'), args.log_level)
    setup_logger(level=log_level, log_file=args.log_file)
    
    # 검색어 수집
    keywords = []
    
    # 우선순위: --quick > --file > 대화형 모드
    if args.quick:
        # 빠른 검색 모드: 명령줄에서 검색어 지정
        keywords.extend(args.quick)
        logger.info(f"빠른 검색 모드: {len(keywords)}개의 검색어를 처리합니다.")
    elif args.file:
        # 파일에서 검색어 읽기
        keywords.extend(load_keywords_from_file(args.file))
    else:
        # 대화형 모드 (기본 동작)
        logger.info("=" * 60)
        logger.info("도매꾹 상품 검색 도구 - 대화형 모드")
        logger.info("=" * 60)
        logger.info("\n검색어를 입력하세요 (여러 개는 쉼표로 구분):")
        logger.info("예시: 양말, 장갑, 모자")
        logger.info("또는: 양말")
        logger.info("")
        
        user_input = input("검색어: ").strip()
        
        if not user_input:
            logger.warning("검색어가 입력되지 않았습니다. 기본값 '양말'을 사용합니다.")
            keywords = ['양말']
        elif ',' in user_input:
            # 쉼표로 구분된 여러 검색어
            keywords = [kw.strip() for kw in user_input.split(',') if kw.strip()]
        else:
            # 단일 검색어
            keywords = [user_input]
    
    if not keywords:
        logger.error("검색어가 없습니다.")
        sys.exit(1)
    
    logger.info(f"\n총 {len(keywords)}개의 검색어를 처리합니다:")
    for idx, kw in enumerate(keywords, 1):
        logger.info(f"  {idx}. {kw}")
    
    # 가격 필터 설정
    min_price = None if args.no_price_filter else args.min_price
    
    # 로그인 정보
    username = args.username or get_username()
    password = args.password or get_password()
    
    # driver는 한 번만 생성하고 재사용
    driver = None
    
    try:
        # 각 검색어마다 순차 처리
        for search_idx, search_keyword in enumerate(keywords, 1):
            logger.info("\n" + "=" * 60)
            logger.info(f"[{search_idx}/{len(keywords)}] 검색어: '{search_keyword}'")
            logger.info("=" * 60)
            
            # 첫 번째 검색어일 때만 driver 생성 (로그인 포함)
            if driver is None:
                search_result = search_products(
                    search_keyword,
                    headless=args.headless,
                    max_results=args.max_results,
                    use_direct_url=not args.use_form,
                    min_price=min_price,
                    username=username,
                    password=password,
                    return_driver=True
                )
                
                # 결과와 driver 분리
                if isinstance(search_result, tuple):
                    results, driver = search_result
                else:
                    results = search_result
                    driver = None
            else:
                # 두 번째 검색어부터는 기존 driver 재사용
                from urllib.parse import quote
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                import time
                
                from config import SEARCH_URL_TEMPLATE
                
                encoded_keyword = quote(search_keyword, safe='')
                search_url = SEARCH_URL_TEMPLATE.format(keyword=encoded_keyword)
                driver.get(search_url)
                logger.info(f"검색 URL로 이동: {search_url}")
                
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)
                
                results = parse_search_results(driver, max_results=args.max_results, min_price=min_price)
            
            # 결과 출력
            if results:
                print_results(results, verbose=args.verbose)
                
                # 결과 저장
                if not args.no_save:
                    save_results(results, search_keyword, output_format=args.format)
                
                # 마이박스에 상품 추가 (옵션)
                if driver and not args.no_mybox:
                    product_ids = [p.get('product_id') for p in results if p.get('product_id')]
                    
                    if product_ids:
                        logger.info("\n" + "=" * 60)
                        logger.info(f"마이박스에 {len(product_ids)}개 상품 추가 및 스피드고 전송 시도")
                        logger.info("=" * 60)
                        
                        success = add_products_to_mybox(driver, product_ids=product_ids, select_all=False)
                        
                        if success:
                            logger.info(f"검색어 '{search_keyword}' 처리 완료!")
                        else:
                            logger.warning(f"검색어 '{search_keyword}' 처리 실패")
                    else:
                        logger.warning(f"검색어 '{search_keyword}': 상품번호를 찾을 수 없어 마이박스담기를 건너뜁니다.")
            else:
                logger.info(f"검색어 '{search_keyword}': 검색 결과가 없습니다.")
            
            # 다음 검색어 처리 전 잠시 대기
            if search_idx < len(keywords):
                logger.info("\n다음 검색어로 이동합니다...")
                import time
                time.sleep(2)
    
    finally:
        # driver 종료
        if driver:
            logger.info("\n브라우저를 종료합니다...")
            driver.quit()
    
    logger.info("\n" + "=" * 60)
    logger.info("모든 검색어 처리 완료!")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
