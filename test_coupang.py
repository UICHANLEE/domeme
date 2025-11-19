"""
쿠팡 쇼핑몰 검색 테스트 스크립트
"""
from scraper import get_chrome_driver
from coupang_shopping import search_coupang_products
from logger import default_logger as logger

def test_coupang_search():
    """쿠팡 쇼핑몰 검색 테스트"""
    logger.info("쿠팡 쇼핑몰 검색 테스트 시작...")
    
    # 드라이버 생성 (headless=False로 브라우저 확인 가능)
    driver = None
    try:
        driver = get_chrome_driver(headless=False)
        logger.info("Chrome 드라이버 생성 완료")
        
        # 검색 테스트
        keyword = "양말"
        logger.info(f"검색어: '{keyword}'")
        
        results = search_coupang_products(
            driver=driver,
            keyword=keyword,
            max_results=10,
            min_price=None,
            max_price=None
        )
        
        logger.info(f"\n{'='*60}")
        logger.info(f"검색 결과: {len(results)}개 상품 발견")
        logger.info(f"{'='*60}\n")
        
        # 결과 출력
        for idx, product in enumerate(results, 1):
            logger.info(f"[{idx}] {product.get('name', 'N/A')}")
            logger.info(f"    가격: {product.get('price', 'N/A')}")
            logger.info(f"    링크: {product.get('link', 'N/A')[:80]}...")
            logger.info(f"    이미지: {product.get('image', 'N/A')[:60]}...")
            logger.info("")
        
        if results:
            logger.info("✓ 쿠팡 검색 테스트 성공!")
            return True
        else:
            logger.warning("⚠ 검색 결과가 없습니다. CSS 선택자를 확인하세요.")
            return False
            
    except Exception as e:
        logger.error(f"✗ 쿠팡 검색 테스트 실패: {e}", exc_info=True)
        return False
    finally:
        if driver:
            logger.info("브라우저 종료 중...")
            driver.quit()

if __name__ == "__main__":
    test_coupang_search()

