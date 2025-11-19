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
from trending import (
    get_trending_keywords, 
    get_keywords_from_result_files,
    get_trending_keywords_from_multiple_sources
)
from coupang_shopping import search_coupang_products
from naver_shopping import search_naver_shopping_products
from gmarket_shopping import search_gmarket_products
from st11_shopping import search_11st_products  # 파일명: 11st_shopping.py
from auction_shopping import search_auction_products
from interpark_shopping import search_interpark_products
from tmon_shopping import search_tmon_products
from wemakeprice_shopping import search_wemakeprice_products

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
            # 모든 결과에서 모든 필드명 수집
            all_fieldnames = set()
            for result in results:
                all_fieldnames.update(result.keys())
            
            # 필드명 정렬 (search_keyword를 맨 앞으로)
            fieldnames = sorted(all_fieldnames)
            if 'search_keyword' in fieldnames:
                fieldnames.remove('search_keyword')
                fieldnames.insert(0, 'search_keyword')
            
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

def extract_product_names_from_results_file(file_path: str, max_products: Optional[int] = None) -> List[str]:
    """
    검색 결과 파일(CSV/JSON)에서 상품명 추출
    
    Args:
        file_path: 검색 결과 파일 경로 (CSV 또는 JSON)
        max_products: 최대 추출할 상품 수 (None이면 모두)
    
    Returns:
        상품명 리스트
    """
    product_names = []
    
    try:
        if file_path.endswith('.csv'):
            import csv
            with open(file_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    if max_products and idx >= max_products:
                        break
                    name = row.get('name', '').strip()
                    if name:
                        product_names.append(name)
        
        elif file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for idx, item in enumerate(data):
                        if max_products and idx >= max_products:
                            break
                        name = item.get('name', '').strip()
                        if name:
                            product_names.append(name)
                elif isinstance(data, dict):
                    name = data.get('name', '').strip()
                    if name:
                        product_names.append(name)
        
        logger.info(f"파일에서 {len(product_names)}개의 상품명을 추출했습니다: {file_path}")
        
    except Exception as e:
        logger.error(f"파일에서 상품명 추출 실패: {e}")
    
    return product_names

def register_products_from_results(
    results_file: str,
    max_products: Optional[int] = None,
    max_results_per_product: Optional[int] = None,
    min_price: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    headless: bool = False
) -> bool:
    """
    검색 결과 파일에서 상품명을 추출하여 도매꾹에서 검색하고 마이박스에 등록
    
    Args:
        results_file: 검색 결과 파일 경로 (CSV 또는 JSON)
        max_products: 최대 처리할 상품 수 (None이면 모두)
        max_results_per_product: 상품당 최대 검색 결과 수
        min_price: 최소 가격 필터
        username: 로그인 아이디
        password: 로그인 비밀번호
        headless: 헤드리스 모드
    
    Returns:
        성공 여부
    """
    try:
        logger.info("=" * 60)
        logger.info("검색 결과 파일에서 상품 등록 시작")
        logger.info("=" * 60)
        
        # 상품명 추출
        product_names = extract_product_names_from_results_file(results_file, max_products)
        
        if not product_names:
            logger.error("추출된 상품명이 없습니다.")
            return False
        
        logger.info(f"총 {len(product_names)}개의 상품명을 처리합니다.")
        
        # 드라이버 생성 및 로그인
        driver = get_chrome_driver(headless=headless)
        
        try:
            # 로그인
            if username and password:
                from login import login_to_domeggook
                login_to_domeggook(driver, username=username, password=password)
            
            all_product_ids = []
            
            # 각 상품명으로 도매꾹에서 검색
            for idx, product_name in enumerate(product_names, 1):
                logger.info("\n" + "=" * 60)
                logger.info(f"[{idx}/{len(product_names)}] 상품명: '{product_name}'")
                logger.info("=" * 60)
                
                try:
                    # 도매꾹에서 검색
                    search_result = search_products(
                        product_name,
                        headless=headless,
                        max_results=max_results_per_product or DEFAULT_MAX_RESULTS,
                        use_direct_url=True,
                        min_price=min_price,
                        username=username,
                        password=password,
                        return_driver=False,
                        driver=driver
                    )
                    
                    if search_result and isinstance(search_result, list):
                        # 검색 결과에서 상품 ID 추출
                        product_ids = [p.get('product_id') for p in search_result if p.get('product_id')]
                        if product_ids:
                            all_product_ids.extend(product_ids)
                            logger.info(f"  ✓ {len(product_ids)}개 상품 발견")
                        else:
                            logger.warning(f"  ⚠ 상품번호를 찾을 수 없음")
                    else:
                        logger.warning(f"  ⚠ 검색 결과 없음")
                
                except Exception as e:
                    logger.error(f"  ✗ 검색 실패: {e}")
                    continue
            
            # 모든 상품을 마이박스에 추가
            if all_product_ids:
                logger.info("\n" + "=" * 60)
                logger.info(f"총 {len(all_product_ids)}개 상품을 마이박스에 추가합니다")
                logger.info("=" * 60)
                
                # 중복 제거
                unique_product_ids = list(dict.fromkeys(all_product_ids))
                logger.info(f"중복 제거 후: {len(unique_product_ids)}개 상품")
                
                # 마이박스에 추가
                success = add_products_to_mybox(driver, product_ids=unique_product_ids, select_all=False)
                
                if success:
                    logger.info("상품 등록 완료!")
                    return True
                else:
                    logger.error("상품 등록 실패")
                    return False
            else:
                logger.warning("등록할 상품이 없습니다.")
                return False
        
        finally:
            driver.quit()
    
    except Exception as e:
        logger.error(f"상품 등록 중 오류 발생: {e}", exc_info=True)
        return False

def convert_json_to_csv(result_dir: str = RESULT_DIR, overwrite: bool = False) -> int:
    """
    result 폴더의 모든 JSON 파일을 CSV로 변환
    
    Args:
        result_dir: 결과 파일이 있는 디렉토리
        overwrite: 기존 CSV 파일이 있으면 덮어쓸지 여부
    
    Returns:
        변환된 파일 개수
    """
    import csv
    import glob
    
    if not os.path.exists(result_dir):
        logger.warning(f"'{result_dir}' 폴더가 존재하지 않습니다.")
        return 0
    
    # JSON 파일 찾기
    json_files = glob.glob(os.path.join(result_dir, "*.json"))
    
    if not json_files:
        logger.info(f"'{result_dir}' 폴더에 JSON 파일이 없습니다.")
        return 0
    
    logger.info(f"총 {len(json_files)}개의 JSON 파일을 찾았습니다.")
    logger.info("=" * 60)
    
    converted_count = 0
    skipped_count = 0
    error_count = 0
    
    for json_file in json_files:
        try:
            # 파일명에서 키워드 추출
            base_name = os.path.basename(json_file)
            keyword = base_name.replace("search_results_", "").replace(".json", "")
            
            # CSV 파일 경로
            csv_file = json_file.replace(".json", ".csv")
            
            # 이미 CSV 파일이 있고 overwrite가 False면 스킵
            if os.path.exists(csv_file) and not overwrite:
                logger.debug(f"  스킵: {base_name} (CSV 파일이 이미 존재)")
                skipped_count += 1
                continue
            
            # JSON 파일 읽기
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not data:
                logger.debug(f"  스킵: {base_name} (데이터가 비어있음)")
                skipped_count += 1
                continue
            
            # CSV 파일로 저장
            if isinstance(data, list) and len(data) > 0:
                fieldnames = data[0].keys()
                with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
                
                logger.info(f"  ✓ 변환 완료: {base_name} → {len(data)}개 상품")
                converted_count += 1
            else:
                logger.warning(f"  경고: {base_name} (유효하지 않은 데이터 형식)")
                error_count += 1
                
        except json.JSONDecodeError as e:
            logger.error(f"  ✗ JSON 파싱 실패: {base_name} - {e}")
            error_count += 1
        except Exception as e:
            logger.error(f"  ✗ 변환 실패: {base_name} - {e}")
            error_count += 1
    
    logger.info("=" * 60)
    logger.info(f"변환 완료!")
    logger.info(f"  - 성공: {converted_count}개")
    if skipped_count > 0:
        logger.info(f"  - 스킵: {skipped_count}개 (이미 CSV 파일 존재)")
    if error_count > 0:
        logger.info(f"  - 실패: {error_count}개")
    
    return converted_count

def merge_csv_files(result_dir: str = RESULT_DIR, output_file: str = None, add_keyword_column: bool = True) -> str:
    """
    result 폴더의 모든 CSV 파일을 하나의 통합 CSV 파일로 병합
    
    Args:
        result_dir: 결과 파일이 있는 디렉토리
        output_file: 출력 파일 경로 (None이면 자동 생성)
        add_keyword_column: 검색어 컬럼 추가 여부
    
    Returns:
        생성된 통합 CSV 파일 경로
    """
    import csv
    import glob
    from datetime import datetime
    
    if not os.path.exists(result_dir):
        logger.warning(f"'{result_dir}' 폴더가 존재하지 않습니다.")
        return ""
    
    # CSV 파일 찾기
    csv_files = glob.glob(os.path.join(result_dir, "search_results_*.csv"))
    
    if not csv_files:
        logger.warning(f"'{result_dir}' 폴더에 CSV 파일이 없습니다.")
        return ""
    
    logger.info(f"총 {len(csv_files)}개의 CSV 파일을 찾았습니다.")
    logger.info("=" * 60)
    
    # 출력 파일명 생성 (프로젝트 루트에 저장)
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 프로젝트 루트 디렉토리 (스크립트가 있는 디렉토리)
        project_root = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(project_root, f"merged_results_{timestamp}.csv")
    elif not os.path.isabs(output_file):
        # 상대 경로인 경우 프로젝트 루트 기준으로 변환
        project_root = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(project_root, output_file)
    
    all_rows = []
    all_fieldnames = set()
    processed_count = 0
    total_rows = 0
    error_count = 0
    
    # 모든 CSV 파일 읽기
    for csv_file in csv_files:
        try:
            # 파일명에서 키워드 추출
            base_name = os.path.basename(csv_file)
            keyword = base_name.replace("search_results_", "").replace(".csv", "")
            
            with open(csv_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                
                # 필드명 수집
                fieldnames = reader.fieldnames
                if fieldnames:
                    all_fieldnames.update(fieldnames)
                    
                    # 각 행 읽기
                    file_rows = 0
                    for row in reader:
                        # 검색어 컬럼 추가
                        if add_keyword_column:
                            row['search_keyword'] = keyword
                        all_rows.append(row)
                        file_rows += 1
                        total_rows += 1
                    
                    if file_rows > 0:
                        logger.info(f"  ✓ 처리 완료: {base_name} → {file_rows}개 상품")
                        processed_count += 1
                    else:
                        logger.debug(f"  스킵: {base_name} (데이터 없음)")
                else:
                    logger.warning(f"  경고: {base_name} (헤더 없음)")
                    error_count += 1
                    
        except Exception as e:
            logger.error(f"  ✗ 읽기 실패: {base_name} - {e}")
            error_count += 1
    
    if not all_rows:
        logger.warning("병합할 데이터가 없습니다.")
        return ""
    
    # 검색어 컬럼을 필드명에 추가
    if add_keyword_column and 'search_keyword' not in all_fieldnames:
        all_fieldnames.add('search_keyword')
    
    # 필드명 정렬 (search_keyword를 맨 앞으로)
    sorted_fieldnames = sorted(all_fieldnames)
    if 'search_keyword' in sorted_fieldnames:
        sorted_fieldnames.remove('search_keyword')
        sorted_fieldnames.insert(0, 'search_keyword')
    
    # 통합 CSV 파일로 저장
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sorted_fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)
        
        logger.info("=" * 60)
        logger.info(f"통합 CSV 파일 생성 완료!")
        logger.info(f"  - 처리된 파일: {processed_count}개")
        logger.info(f"  - 총 상품 수: {total_rows}개")
        logger.info(f"  - 출력 파일: {os.path.basename(output_file)}")
        if error_count > 0:
            logger.info(f"  - 실패: {error_count}개")
        
        return output_file
        
    except Exception as e:
        logger.error(f"통합 CSV 파일 저장 실패: {e}")
        return ""

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
  
  # result 폴더의 모든 JSON 파일을 CSV로 변환
  python main.py --convert-json-to-csv
  
  # CSV 변환 시 기존 파일 덮어쓰기
  python main.py --convert-json-to-csv --overwrite-csv
  
  # result 폴더의 모든 CSV 파일을 하나로 병합
  python main.py --merge-csv
  
  # 통합 CSV 파일의 출력 경로 지정 (프로젝트 루트에 저장)
  python main.py --merge-csv --merge-output all_products.csv
  
  # 검색어 컬럼 없이 병합
  python main.py --merge-csv --no-keyword-column
  
  # 쿠팡 쇼핑몰에서 검색
  python main.py -q 양말 --search-coupang
  
  # 네이버 쇼핑에서 검색
  python main.py -q 양말 --search-naver
  
  # 도매꾹, 쿠팡, 네이버 쇼핑 모두에서 검색
  python main.py -q 양말 --search-all
  
  # 모든 지원 사이트에서 검색 (도매꾹, 쿠팡, 네이버, 지마켓, 11번가, 옥션, 인터파크, 티몬, 위메프)
  python main.py -q 양말 --search-all-sites
  
  # 특정 사이트에서만 검색
  python main.py -q 양말 --search-gmarket
  python main.py -q 양말 --search-11st
  python main.py -q 양말 --search-auction
  python main.py -q 양말 --search-interpark
  python main.py -q 양말 --search-tmon
  python main.py -q 양말 --search-wemakeprice
  
  # 쿠팡에서 검색 + 가격 필터
  python main.py -q 양말 --search-coupang --min-price 10000 --max-price 50000
  
  # 검색 결과 파일에서 상품명 추출하여 도매꾹에서 검색하고 등록
  python main.py --register-from-file merged_results_20251117_154320.csv
  
  # 통합 CSV 파일에서 최대 100개 상품만 등록
  python main.py --register-from-file merged_results_20251117_154320.csv --max-register-products 100
  
  # 검색 결과 파일에서 상품 등록 (상품당 최대 5개 결과)
  python main.py --register-from-file result/search_results_양말.csv --max-results-per-product 5
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
    parser.add_argument(
        '--trending',
        action='store_true',
        help='인기 키워드를 자동으로 수집하여 검색'
    )
    parser.add_argument(
        '--trending-count',
        type=int,
        default=50,
        help='수집할 인기 키워드 개수 (기본값: 50)'
    )
    parser.add_argument(
        '--multi-source',
        action='store_true',
        help='여러 소스를 동시에 활용하여 더 많은 키워드 수집 (8개 사이트: 네이버, 네이버데이터랩, 쿠팡, 쿠팡트렌드, 아이템스카우트, 지마켓, 11번가, 구글트렌드)'
    )
    parser.add_argument(
        '--trending-source',
        choices=['auto', 'products', 'search_suggestions', 'categories', 'results', 
                 'naver', 'coupang', 'itemscout', 'gmarket', '11st', 'google'],
        default='auto',
        help='인기 키워드 수집 소스 (기본값: auto) - naver: 네이버 쇼핑, coupang: 쿠팡, itemscout: 아이템 스카우트, gmarket: 지마켓, 11st: 11번가, google: 구글 트렌드'
    )
    parser.add_argument(
        '--search-coupang',
        action='store_true',
        help='쿠팡 쇼핑몰에서 상품 검색 (도매꾹 대신 쿠팡에서 검색)'
    )
    parser.add_argument(
        '--search-naver',
        action='store_true',
        help='네이버 쇼핑에서 상품 검색 (도매꾹 대신 네이버 쇼핑에서 검색)'
    )
    parser.add_argument(
        '--search-all',
        action='store_true',
        help='도매꾹, 쿠팡, 네이버 쇼핑에서 모두 검색'
    )
    parser.add_argument(
        '--search-gmarket',
        action='store_true',
        help='지마켓에서 상품 검색'
    )
    parser.add_argument(
        '--search-11st',
        action='store_true',
        help='11번가에서 상품 검색'
    )
    parser.add_argument(
        '--search-auction',
        action='store_true',
        help='옥션에서 상품 검색'
    )
    parser.add_argument(
        '--search-interpark',
        action='store_true',
        help='인터파크에서 상품 검색'
    )
    parser.add_argument(
        '--search-tmon',
        action='store_true',
        help='티몬에서 상품 검색'
    )
    parser.add_argument(
        '--search-wemakeprice',
        action='store_true',
        help='위메프에서 상품 검색'
    )
    parser.add_argument(
        '--search-all-sites',
        action='store_true',
        help='모든 지원 사이트에서 검색 (도매꾹, 쿠팡, 네이버, 지마켓, 11번가, 옥션, 인터파크, 티몬, 위메프)'
    )
    parser.add_argument(
        '--max-price',
        type=int,
        help='최대 가격 필터'
    )
    parser.add_argument(
        '--exclude-brands',
        action='store_true',
        help='브랜드 키워드 제외 (일반 키워드만 추출)'
    )
    parser.add_argument(
        '--analyze-competition',
        action='store_true',
        help='경쟁 분석 데이터 포함 (검색수, 상품수, 경쟁강도 등)'
    )
    
    # 검색 옵션
    parser.add_argument(
        '--max-results',
        type=int,
        default=DEFAULT_MAX_RESULTS,
        help=f'가져올 최대 결과 수 (기본값: {DEFAULT_MAX_RESULTS})'
    )
    parser.add_argument(
        '--pages',
        type=int,
        default=1,
        help='가져올 최대 페이지 수 (기본값: 1, 여러 페이지 검색 시 사용)'
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
    parser.add_argument(
        '--convert-json-to-csv',
        action='store_true',
        help='result 폴더의 모든 JSON 파일을 CSV로 변환'
    )
    parser.add_argument(
        '--overwrite-csv',
        action='store_true',
        help='CSV 변환 시 기존 CSV 파일 덮어쓰기 (--convert-json-to-csv와 함께 사용)'
    )
    parser.add_argument(
        '--merge-csv',
        action='store_true',
        help='result 폴더의 모든 CSV 파일을 하나의 통합 CSV 파일로 병합'
    )
    parser.add_argument(
        '--merge-output',
        type=str,
        help='통합 CSV 파일의 출력 경로 (--merge-csv와 함께 사용, 지정하지 않으면 자동 생성)'
    )
    parser.add_argument(
        '--no-keyword-column',
        action='store_true',
        help='통합 CSV에 검색어 컬럼 추가하지 않기 (--merge-csv와 함께 사용)'
    )
    parser.add_argument(
        '--register-from-file',
        type=str,
        help='검색 결과 파일(CSV/JSON)에서 상품명을 추출하여 도매꾹에서 검색하고 마이박스에 등록'
    )
    parser.add_argument(
        '--max-register-products',
        type=int,
        help='등록할 최대 상품 수 (--register-from-file과 함께 사용)'
    )
    parser.add_argument(
        '--max-results-per-product',
        type=int,
        help='상품당 최대 검색 결과 수 (--register-from-file과 함께 사용)'
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
    
    # JSON to CSV 변환 모드
    if args.convert_json_to_csv:
        logger.info("=" * 60)
        logger.info("JSON → CSV 변환 모드")
        logger.info("=" * 60)
        converted = convert_json_to_csv(result_dir=RESULT_DIR, overwrite=args.overwrite_csv)
        logger.info(f"\n총 {converted}개의 파일이 변환되었습니다.")
        sys.exit(0)
    
    # CSV 병합 모드
    if args.merge_csv:
        logger.info("=" * 60)
        logger.info("CSV 파일 병합 모드")
        logger.info("=" * 60)
        output_file = merge_csv_files(
            result_dir=RESULT_DIR,
            output_file=args.merge_output,
            add_keyword_column=not args.no_keyword_column
        )
        if output_file:
            logger.info(f"\n통합 파일이 생성되었습니다: {output_file}")
        sys.exit(0)
    
    # 상품 등록 모드 (검색 결과 파일에서 상품명 추출하여 등록)
    if args.register_from_file:
        logger.info("=" * 60)
        logger.info("검색 결과 파일에서 상품 등록 모드")
        logger.info("=" * 60)
        
        # 파일 경로 확인
        results_file = args.register_from_file
        if not os.path.isabs(results_file):
            # 상대 경로인 경우 프로젝트 루트 기준으로 변환
            project_root = os.path.dirname(os.path.abspath(__file__))
            results_file = os.path.join(project_root, results_file)
        
        if not os.path.exists(results_file):
            logger.error(f"파일을 찾을 수 없습니다: {results_file}")
            sys.exit(1)
        
        # 로그인 정보
        username = args.username or get_username()
        password = args.password or get_password()
        
        # 가격 필터 설정
        min_price = None if args.no_price_filter else args.min_price
        
        # 상품 등록 실행
        success = register_products_from_results(
            results_file=results_file,
            max_products=args.max_register_products,
            max_results_per_product=args.max_results_per_product or args.max_results,
            min_price=min_price,
            username=username,
            password=password,
            headless=args.headless
        )
        
        if success:
            logger.info("\n상품 등록이 완료되었습니다!")
        else:
            logger.error("\n상품 등록 중 오류가 발생했습니다.")
            sys.exit(1)
        
        sys.exit(0)
    
    # 검색어 수집
    keywords = []
    
    # 우선순위: --quick > --file > --trending > 대화형 모드
    if args.quick:
        # 빠른 검색 모드: 명령줄에서 검색어 지정
        keywords.extend(args.quick)
        logger.info(f"빠른 검색 모드: {len(keywords)}개의 검색어를 처리합니다.")
    elif args.file:
        # 파일에서 검색어 읽기
        keywords.extend(load_keywords_from_file(args.file))
    elif args.trending:
        # 인기 키워드 자동 수집 모드
        logger.info("=" * 60)
        logger.info("인기 키워드 자동 수집 모드")
        logger.info("=" * 60)
        
        # driver 생성 (인기 키워드 수집용)
        driver = get_chrome_driver(headless=args.headless)
        try:
            # 로그인 (필요한 경우)
            username = args.username or get_username()
            password = args.password or get_password()
            
            if username and password:
                from login import login_to_domeggook
                login_to_domeggook(driver, username=username, password=password)
            
            # 인기 키워드 수집
            if args.trending_source == 'results':
                # 과거 결과 파일에서 추출
                keywords = get_keywords_from_result_files(
                    result_dir=RESULT_DIR,
                    max_keywords=args.trending_count
                )
                logger.info(f"과거 검색 결과에서 {len(keywords)}개 키워드를 찾았습니다.")
            elif args.multi_source:
                # 여러 소스를 동시에 활용하여 수집
                logger.info("여러 소스에서 키워드를 수집합니다...")
                keywords = get_trending_keywords_from_multiple_sources(
                    driver=driver,
                    max_keywords=args.trending_count,
                    exclude_brands=args.exclude_brands,
                    analyze_competition_data=args.analyze_competition
                )
                logger.info(f"여러 소스에서 총 {len(keywords)}개 인기 키워드를 수집했습니다.")
            else:
                # 웹에서 수집
                keywords = get_trending_keywords(
                    driver=driver,
                    method=args.trending_source,
                    max_keywords=args.trending_count,
                    source=args.trending_source,
                    exclude_brands=args.exclude_brands,
                    analyze_competition_data=args.analyze_competition
                )
                logger.info(f"웹에서 {len(keywords)}개 인기 키워드를 수집했습니다.")
                
                # 브랜드 제외 옵션이 있으면 추가 정보 출력
                if args.exclude_brands:
                    from brand_filter import is_brand_keyword
                    brand_count = sum(1 for kw in keywords if is_brand_keyword(kw))
                    logger.info(f"브랜드 키워드: {brand_count}개, 일반 키워드: {len(keywords) - brand_count}개")
            
            if not keywords:
                logger.warning("인기 키워드를 찾지 못했습니다. 기본 키워드를 사용합니다.")
                keywords = ['양말', '장갑', '모자']
            
            # 키워드 출력
            logger.info("\n수집된 인기 키워드:")
            for idx, kw in enumerate(keywords, 1):
                logger.info(f"  {idx}. {kw}")
            logger.info("")
            
        finally:
            # 인기 키워드 수집 후 driver는 재사용하지 않고 종료
            driver.quit()
            driver = None
        
        if not keywords:
            logger.error("인기 키워드 수집 실패")
            sys.exit(1)
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
    max_price = args.max_price
    
    # 로그인 정보
    username = args.username or get_username()
    password = args.password or get_password()
    
    # 검색 소스 결정
    search_sources = []
    if args.search_all_sites:
        # 모든 지원 사이트에서 검색
        search_sources = ['domeggook', 'coupang', 'naver', 'gmarket', '11st', 'auction', 'interpark', 'tmon', 'wemakeprice']
    elif args.search_all:
        search_sources = ['domeggook', 'coupang', 'naver']
    elif args.search_coupang:
        search_sources = ['coupang']
    elif args.search_naver:
        search_sources = ['naver']
    elif args.search_gmarket:
        search_sources = ['gmarket']
    elif args.search_11st:
        search_sources = ['11st']
    elif args.search_auction:
        search_sources = ['auction']
    elif args.search_interpark:
        search_sources = ['interpark']
    elif args.search_tmon:
        search_sources = ['tmon']
    elif args.search_wemakeprice:
        search_sources = ['wemakeprice']
    else:
        search_sources = ['domeggook']  # 기본값
    
    # driver는 한 번만 생성하고 재사용
    driver = None
    
    try:
        # 각 검색어마다 순차 처리
        for search_idx, search_keyword in enumerate(keywords, 1):
            logger.info("\n" + "=" * 60)
            logger.info(f"[{search_idx}/{len(keywords)}] 검색어: '{search_keyword}'")
            logger.info("=" * 60)
            
            all_results = []
            
            # 각 검색 소스에서 검색
            for source in search_sources:
                logger.info(f"\n[{source.upper()}] 검색 중...")
                
                if source == 'domeggook':
                    # 도매꾹 검색
                    if driver is None:
                        search_result = search_products(
                            search_keyword,
                            headless=args.headless,
                            max_results=args.max_results,
                            use_direct_url=not args.use_form,
                            min_price=min_price,
                            username=username,
                            password=password,
                            return_driver=True,
                            max_pages=args.pages
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
                    
                    if results:
                        all_results.extend(results)
                        logger.info(f"  ✓ 도매꾹: {len(results)}개 상품 발견")
                
                elif source == 'coupang':
                    # 쿠팡 쇼핑몰 검색 (undetected-chromedriver 사용)
                    coupang_driver = None
                    try:
                        from coupang_shopping import search_coupang_products
                        results = search_coupang_products(
                            driver=None,  # 쿠팡 전용 드라이버 자동 생성
                            keyword=search_keyword,
                            max_results=args.max_results,
                            min_price=min_price,
                            max_price=max_price,
                            headless=args.headless
                        )
                        if results:
                            all_results.extend(results)
                            logger.info(f"  ✓ 쿠팡: {len(results)}개 상품 발견")
                        else:
                            logger.warning(f"  ⚠ 쿠팡: 검색 결과 없음")
                    except ImportError as e:
                        logger.error(f"  ✗ 쿠팡 검색 실패: {e}")
                        logger.info(f"  💡 'pip install undetected-chromedriver' 실행 후 다시 시도하세요.")
                    except Exception as e:
                        logger.error(f"  ✗ 쿠팡 검색 실패: {e}")
                        logger.info(f"  💡 네이버 쇼핑(--search-naver) 사용을 권장합니다.")
                    finally:
                        # 쿠팡 드라이버는 별도로 관리 (undetected-chromedriver는 자동 종료됨)
                        pass
                
                elif source == 'naver':
                    # 네이버 쇼핑 검색
                    if driver is None:
                        driver = get_chrome_driver(headless=args.headless)
                    
                    try:
                        results = search_naver_shopping_products(
                            driver=driver,
                            keyword=search_keyword,
                            max_results=args.max_results,
                            min_price=min_price,
                            max_price=max_price
                        )
                        if results:
                            all_results.extend(results)
                            logger.info(f"  ✓ 네이버 쇼핑: {len(results)}개 상품 발견")
                    except Exception as e:
                        logger.error(f"  ✗ 네이버 쇼핑 검색 실패: {e}")
                
                elif source == 'gmarket':
                    # 지마켓 검색
                    if driver is None:
                        driver = get_chrome_driver(headless=args.headless)
                    
                    try:
                        results = search_gmarket_products(
                            driver=driver,
                            keyword=search_keyword,
                            max_results=args.max_results,
                            min_price=min_price,
                            max_price=max_price,
                            headless=args.headless
                        )
                        if results:
                            all_results.extend(results)
                            logger.info(f"  ✓ 지마켓: {len(results)}개 상품 발견")
                    except Exception as e:
                        logger.error(f"  ✗ 지마켓 검색 실패: {e}")
                
                elif source == '11st':
                    # 11번가 검색
                    if driver is None:
                        driver = get_chrome_driver(headless=args.headless)
                    
                    try:
                        results = search_11st_products(
                            driver=driver,
                            keyword=search_keyword,
                            max_results=args.max_results,
                            min_price=min_price,
                            max_price=max_price,
                            headless=args.headless
                        )
                        if results:
                            all_results.extend(results)
                            logger.info(f"  ✓ 11번가: {len(results)}개 상품 발견")
                    except Exception as e:
                        logger.error(f"  ✗ 11번가 검색 실패: {e}")
                
                elif source == 'auction':
                    # 옥션 검색
                    if driver is None:
                        driver = get_chrome_driver(headless=args.headless)
                    
                    try:
                        results = search_auction_products(
                            driver=driver,
                            keyword=search_keyword,
                            max_results=args.max_results,
                            min_price=min_price,
                            max_price=max_price,
                            headless=args.headless
                        )
                        if results:
                            all_results.extend(results)
                            logger.info(f"  ✓ 옥션: {len(results)}개 상품 발견")
                    except Exception as e:
                        logger.error(f"  ✗ 옥션 검색 실패: {e}")
                
                elif source == 'interpark':
                    # 인터파크 검색
                    if driver is None:
                        driver = get_chrome_driver(headless=args.headless)
                    
                    try:
                        results = search_interpark_products(
                            driver=driver,
                            keyword=search_keyword,
                            max_results=args.max_results,
                            min_price=min_price,
                            max_price=max_price,
                            headless=args.headless
                        )
                        if results:
                            all_results.extend(results)
                            logger.info(f"  ✓ 인터파크: {len(results)}개 상품 발견")
                    except Exception as e:
                        logger.error(f"  ✗ 인터파크 검색 실패: {e}")
                
                elif source == 'tmon':
                    # 티몬 검색
                    if driver is None:
                        driver = get_chrome_driver(headless=args.headless)
                    
                    try:
                        results = search_tmon_products(
                            driver=driver,
                            keyword=search_keyword,
                            max_results=args.max_results,
                            min_price=min_price,
                            max_price=max_price,
                            headless=args.headless
                        )
                        if results:
                            all_results.extend(results)
                            logger.info(f"  ✓ 티몬: {len(results)}개 상품 발견")
                    except Exception as e:
                        logger.error(f"  ✗ 티몬 검색 실패: {e}")
                
                elif source == 'wemakeprice':
                    # 위메프 검색
                    if driver is None:
                        driver = get_chrome_driver(headless=args.headless)
                    
                    try:
                        results = search_wemakeprice_products(
                            driver=driver,
                            keyword=search_keyword,
                            max_results=args.max_results,
                            min_price=min_price,
                            max_price=max_price,
                            headless=args.headless
                        )
                        if results:
                            all_results.extend(results)
                            logger.info(f"  ✓ 위메프: {len(results)}개 상품 발견")
                    except Exception as e:
                        logger.error(f"  ✗ 위메프 검색 실패: {e}")
            
            # 통합 결과 사용
            results = all_results
            
            # 결과 출력
            if results:
                print_results(results, verbose=args.verbose)
                
                # 결과 저장
                if not args.no_save:
                    save_results(results, search_keyword, output_format=args.format)
                
                # 마이박스에 상품 추가 (옵션) - 도매꾹에서만 가능
                if driver and not args.no_mybox and 'domeggook' in search_sources:
                    # 도매꾹 상품만 필터링 (다른 사이트 제외)
                    other_sources = ['coupang', 'naver_shopping', 'gmarket', '11st', 'auction', 'interpark', 'tmon', 'wemakeprice']
                    domeggook_results = [p for p in results if p.get('source') not in other_sources]
                    product_ids = [p.get('product_id') for p in domeggook_results if p.get('product_id')]
                    
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
