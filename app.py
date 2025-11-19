"""
도매꾹 검색 도구 - Streamlit GUI
"""
import streamlit as st
import sys
import os
import tempfile
from pathlib import Path
from typing import List, Optional

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    RESULT_DIR, DEFAULT_MAX_RESULTS, DEFAULT_MIN_PRICE,
    get_username, get_password
)
from main import (
    save_results, print_results, load_keywords_from_file,
    convert_json_to_csv, merge_csv_files, register_products_from_results
)
from logger import setup_logger, default_logger as logger

# 페이지 설정
st.set_page_config(
    page_title="도매꾹 검색 도구",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 0.5rem;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f0f2f6;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'search_running' not in st.session_state:
    st.session_state.search_running = False
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'search_keywords' not in st.session_state:
    st.session_state.search_keywords = []

def run_search_with_gui():
    """GUI에서 검색 실행"""
    try:
        # 검색어 수집
        keywords = []
        
        # 검색어 입력 방식 선택
        search_mode = st.sidebar.radio(
            "검색어 입력 방식",
            ["직접 입력", "파일 업로드", "인기 키워드 자동 수집"],
            index=0
        )
        
        if search_mode == "직접 입력":
            keyword_input = st.sidebar.text_input(
                "검색어 입력",
                placeholder="예: 양말, 장갑, 모자 (여러 개는 쉼표로 구분)",
                help="여러 검색어를 쉼표로 구분하여 입력할 수 있습니다."
            )
            if keyword_input:
                keywords = [kw.strip() for kw in keyword_input.split(',') if kw.strip()]
        
        elif search_mode == "파일 업로드":
            uploaded_file = st.sidebar.file_uploader(
                "검색어 파일 업로드",
                type=['txt'],
                help="한 줄에 하나씩 검색어를 입력한 텍스트 파일을 업로드하세요."
            )
            if uploaded_file:
                # 임시 파일로 저장
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp_file:
                    tmp_file.write(uploaded_file.read().decode('utf-8'))
                    tmp_path = tmp_file.name
                
                keywords = load_keywords_from_file(tmp_path)
                os.unlink(tmp_path)  # 임시 파일 삭제
        
        elif search_mode == "인기 키워드 자동 수집":
            st.sidebar.markdown("**각 마켓에서 인기 검색어를 가져와 도매꾹에서 검색합니다.**")
            
            # 각 마켓별 키워드 수집 옵션
            st.sidebar.markdown("#### 📊 키워드 수집 마켓 선택")
            
            collect_naver = st.sidebar.checkbox("네이버 쇼핑", value=True, help="네이버 쇼핑 베스트 상품명에서 키워드 수집")
            collect_coupang = st.sidebar.checkbox("쿠팡", value=True, help="쿠팡 베스트셀러에서 키워드 수집")
            collect_gmarket = st.sidebar.checkbox("지마켓", value=True, help="지마켓 베스트 상품에서 키워드 수집")
            collect_11st = st.sidebar.checkbox("11번가", value=False, help="11번가 베스트셀러에서 키워드 수집")
            collect_itemscout = st.sidebar.checkbox("아이템스카우트", value=False, help="아이템스카우트 트렌드에서 키워드 수집")
            collect_google = st.sidebar.checkbox("구글 트렌드", value=False, help="구글 트렌드에서 키워드 수집")
            
            trending_count = st.sidebar.number_input(
                "수집할 키워드 개수",
                min_value=1,
                max_value=500,
                value=100,
                step=10,
                help="선택한 모든 마켓에서 합쳐서 이 개수만큼 수집합니다."
            )
            
            exclude_brands = st.sidebar.checkbox(
                "브랜드 키워드 제외",
                value=True,
                help="브랜드명이 포함된 키워드는 제외합니다."
            )
            
            if st.sidebar.button("🔍 키워드 수집 및 검색 시작", type="primary"):
                with st.spinner("각 마켓에서 인기 키워드를 수집하는 중..."):
                    from scraper import get_chrome_driver
                    from trending import get_trending_keywords_from_multiple_sources, get_trending_keywords
                    
                    driver = get_chrome_driver(headless=True)
                    all_keywords = []
                    
                    try:
                        # 선택한 마켓에서 키워드 수집
                        per_source_count = max(trending_count // 6, 20)  # 마켓당 최소 20개
                        
                        if collect_naver:
                            try:
                                st.info("네이버 쇼핑에서 키워드 수집 중...")
                                naver_kw = get_trending_keywords(
                                    driver=driver,
                                    method='naver',
                                    max_keywords=per_source_count,
                                    source='naver',
                                    exclude_brands=exclude_brands
                                )
                                if naver_kw:
                                    all_keywords.extend(naver_kw)
                                    st.success(f"✓ 네이버: {len(naver_kw)}개")
                            except Exception as e:
                                st.warning(f"네이버 수집 실패: {e}")
                        
                        if collect_coupang:
                            try:
                                st.info("쿠팡에서 키워드 수집 중...")
                                coupang_kw = get_trending_keywords(
                                    driver=driver,
                                    method='coupang',
                                    max_keywords=per_source_count,
                                    source='coupang',
                                    exclude_brands=exclude_brands
                                )
                                if coupang_kw:
                                    all_keywords.extend(coupang_kw)
                                    st.success(f"✓ 쿠팡: {len(coupang_kw)}개")
                            except Exception as e:
                                st.warning(f"쿠팡 수집 실패: {e}")
                        
                        if collect_gmarket:
                            try:
                                st.info("지마켓에서 키워드 수집 중...")
                                gmarket_kw = get_trending_keywords(
                                    driver=driver,
                                    method='gmarket',
                                    max_keywords=per_source_count,
                                    source='gmarket',
                                    exclude_brands=exclude_brands
                                )
                                if gmarket_kw:
                                    all_keywords.extend(gmarket_kw)
                                    st.success(f"✓ 지마켓: {len(gmarket_kw)}개")
                            except Exception as e:
                                st.warning(f"지마켓 수집 실패: {e}")
                        
                        if collect_11st:
                            try:
                                st.info("11번가에서 키워드 수집 중...")
                                st11_kw = get_trending_keywords(
                                    driver=driver,
                                    method='11st',
                                    max_keywords=per_source_count,
                                    source='11st',
                                    exclude_brands=exclude_brands
                                )
                                if st11_kw:
                                    all_keywords.extend(st11_kw)
                                    st.success(f"✓ 11번가: {len(st11_kw)}개")
                            except Exception as e:
                                st.warning(f"11번가 수집 실패: {e}")
                        
                        if collect_itemscout:
                            try:
                                st.info("아이템스카우트에서 키워드 수집 중...")
                                itemscout_kw = get_trending_keywords(
                                    driver=driver,
                                    method='itemscout',
                                    max_keywords=per_source_count,
                                    source='itemscout',
                                    exclude_brands=exclude_brands
                                )
                                if itemscout_kw:
                                    all_keywords.extend(itemscout_kw)
                                    st.success(f"✓ 아이템스카우트: {len(itemscout_kw)}개")
                            except Exception as e:
                                st.warning(f"아이템스카우트 수집 실패: {e}")
                        
                        if collect_google:
                            try:
                                st.info("구글 트렌드에서 키워드 수집 중...")
                                google_kw = get_trending_keywords(
                                    driver=driver,
                                    method='google',
                                    max_keywords=per_source_count,
                                    source='google',
                                    exclude_brands=exclude_brands
                                )
                                if google_kw:
                                    all_keywords.extend(google_kw)
                                    st.success(f"✓ 구글 트렌드: {len(google_kw)}개")
                            except Exception as e:
                                st.warning(f"구글 트렌드 수집 실패: {e}")
                        
                        # 중복 제거
                        keywords = list(dict.fromkeys(all_keywords))[:trending_count]
                        st.session_state.search_keywords = keywords
                        st.sidebar.success(f"✅ 총 {len(keywords)}개 키워드 수집 완료!")
                        
                        # 자동으로 검색 시작
                        if keywords:
                            st.info(f"수집된 키워드로 도매꾹 검색을 시작합니다...")
                            keywords = st.session_state.search_keywords
                    finally:
                        driver.quit()
        
        # 검색어가 없으면 수집된 키워드 사용
        if not keywords and st.session_state.search_keywords:
            keywords = st.session_state.search_keywords
        
        if not keywords:
            st.warning("⚠️ 검색어를 입력하거나 선택해주세요.")
            return
        
        # 도매꾹에서만 검색 (고정)
        st.sidebar.markdown("---")
        st.sidebar.info("ℹ️ **도매꾹에서만 검색합니다.**\n\n각 마켓은 인기 키워드 수집용으로만 사용됩니다.")
        
        # 검색 옵션
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ⚙️ 검색 옵션")
        
        max_results = st.sidebar.number_input(
            "최대 결과 수",
            min_value=1,
            max_value=1000,
            value=DEFAULT_MAX_RESULTS,
            step=1
        )
        
        pages = st.sidebar.number_input(
            "최대 페이지 수",
            min_value=1,
            max_value=50,
            value=1,
            step=1
        )
        
        use_price_filter = st.sidebar.checkbox("가격 필터 사용", value=True)
        min_price = None
        max_price = None
        
        if use_price_filter:
            min_price = st.sidebar.number_input(
                "최소 가격 (원)",
                min_value=0,
                value=DEFAULT_MIN_PRICE,
                step=1000
            )
            max_price = st.sidebar.number_input(
                "최대 가격 (원)",
                min_value=0,
                value=0,
                step=1000,
                help="0으로 설정하면 최대 가격 제한 없음"
            )
            if max_price == 0:
                max_price = None
        
        # 실행 옵션
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🚀 실행 옵션")
        
        headless = st.sidebar.checkbox(
            "헤드리스 모드",
            value=True,
            help="브라우저 창을 숨깁니다."
        )
        
        add_to_mybox = st.sidebar.checkbox(
            "마이박스에 자동 추가",
            value=True,
            help="검색 결과를 마이박스에 자동으로 추가합니다. (기본값: 활성화)"
        )
        
        use_form = st.sidebar.checkbox(
            "검색 폼 사용",
            value=False,
            help="검색 폼을 사용하는 방식 (기본값: 직접 URL 접근)"
        )
        
        # 출력 옵션
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📤 출력 옵션")
        
        output_format = st.sidebar.selectbox(
            "결과 저장 형식",
            ['json', 'csv'],
            index=0
        )
        
        save_results_option = st.sidebar.checkbox(
            "결과 파일 저장",
            value=True
        )
        
        verbose = st.sidebar.checkbox(
            "상세 출력",
            value=False
        )
        
        # 로그인 정보
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔐 로그인 정보")
        
        username = st.sidebar.text_input(
            "아이디",
            value=get_username() or "",
            type="default"
        )
        
        password = st.sidebar.text_input(
            "비밀번호",
            value="",
            type="password",
            help="환경변수 DOMPWD가 설정되어 있으면 자동으로 사용됩니다."
        )
        
        if not password:
            password = get_password()
        
        # 검색 실행 버튼
        st.sidebar.markdown("---")
        search_button = st.sidebar.button(
            "🔍 검색 시작",
            type="primary",
            use_container_width=True
        )
        
        # 메인 영역
        st.markdown('<div class="main-header">🔍 도매꾹 검색 도구</div>', unsafe_allow_html=True)
        
        if search_button:
            if not keywords:
                st.error("❌ 검색어를 입력해주세요.")
                return
            
            st.session_state.search_running = True
            st.session_state.search_results = []
            
            # 검색 실행
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            all_results = []
            
            # 도매꾹에서만 검색 (드라이버 재사용)
            from search import search_products
            from scraper import get_chrome_driver
            from login import login_to_domeggook
            
            driver = None
            try:
                # 드라이버 생성 및 로그인
                driver = get_chrome_driver(headless=headless)
                if username and password:
                    login_to_domeggook(driver, username=username, password=password)
                
                for search_idx, search_keyword in enumerate(keywords):
                    status_text.text(f"도매꾹 검색 중: {search_keyword} ({search_idx + 1}/{len(keywords)})")
                    progress_bar.progress((search_idx + 1) / len(keywords))
                    
                    try:
                        # 도매꾹에서 검색
                        results = search_products(
                            search_keyword,
                            headless=headless,
                            max_results=max_results,
                            use_direct_url=not use_form,
                            min_price=min_price,
                            username=username or None,
                            password=password or None,
                            return_driver=False,
                            driver=driver,  # 드라이버 재사용
                            max_pages=pages
                        )
                        
                        if results:
                            # 검색어 정보 추가
                            for result in results:
                                result['search_keyword'] = search_keyword
                            all_results.extend(results)
                            st.success(f"✓ '{search_keyword}': {len(results)}개 상품 발견")
                        else:
                            st.info(f"ℹ️ '{search_keyword}': 검색 결과 없음")
                    
                    except Exception as e:
                        st.warning(f"⚠️ '{search_keyword}' 검색 중 오류: {str(e)}")
                        logger.error(f"검색 오류 ({search_keyword}): {e}", exc_info=True)
                        continue
            finally:
                if driver:
                    driver.quit()
            
            progress_bar.progress(1.0)
            status_text.text("검색 완료!")
            
            st.session_state.search_results = all_results
            st.session_state.search_running = False
            
            # 결과 저장
            if save_results_option and all_results:
                for keyword in keywords:
                    keyword_results = [r for r in all_results if r.get('search_keyword') == keyword]
                    if keyword_results:
                        save_results(keyword_results, keyword, output_format=output_format)
            
            # 마이박스에 자동 추가
            if add_to_mybox and all_results:
                product_ids = [r.get('product_id') for r in all_results if r.get('product_id')]
                
                if product_ids:
                    # 중복 제거
                    unique_product_ids = list(dict.fromkeys(product_ids))
                    
                    st.info(f"마이박스에 {len(unique_product_ids)}개 상품 추가 중...")
                    
                    from scraper import get_chrome_driver
                    from mybox import add_products_to_mybox
                    from login import login_to_domeggook
                    
                    driver = get_chrome_driver(headless=headless)
                    try:
                        if username and password:
                            login_to_domeggook(driver, username=username, password=password)
                        
                        success = add_products_to_mybox(driver, product_ids=unique_product_ids, select_all=False)
                        if success:
                            st.success(f"✅ 마이박스에 {len(unique_product_ids)}개 상품이 추가되었습니다!")
                        else:
                            st.error("❌ 마이박스 추가 실패")
                    finally:
                        driver.quit()
                else:
                    st.warning("⚠️ 상품번호를 찾을 수 없어 마이박스 추가를 건너뜁니다.")
            
            st.success(f"✅ 검색 완료! 총 {len(all_results)}개 상품을 찾았습니다.")
        
        # 결과 표시
        if st.session_state.search_results:
            st.markdown('<div class="section-header">📊 검색 결과</div>', unsafe_allow_html=True)
            
            results = st.session_state.search_results
            
            # 통계 정보
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("총 상품 수", len(results))
            with col2:
                unique_keywords = len(set(r.get('search_keyword', '') for r in results))
                st.metric("검색어 수", unique_keywords)
            with col3:
                st.metric("검색 소스", "도매꾹")
            with col4:
                if results:
                    prices = [r.get('price_value', 0) for r in results if r.get('price_value')]
                    if prices:
                        avg_price = sum(prices) / len(prices)
                        st.metric("평균 가격", f"{avg_price:,.0f}원")
            
            # 결과 테이블
            if verbose:
                for idx, product in enumerate(results[:100], 1):  # 최대 100개만 표시
                    with st.expander(f"[{idx}] {product.get('name', 'N/A')}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**가격:** {product.get('price', 'N/A')}")
                            st.write(f"**판매자:** {product.get('seller', 'N/A')}")
                            st.write(f"**등급:** {product.get('grade', 'N/A')}")
                        with col2:
                            st.write(f"**상품번호:** {product.get('product_id', 'N/A')}")
                            st.write(f"**소스:** {product.get('source', 'domeggook')}")
                            if product.get('link'):
                                st.markdown(f"[상품 링크]({product['link']})")
            else:
                # 간단한 테이블
                display_results = []
                for product in results[:100]:  # 최대 100개만 표시
                    display_results.append({
                        '상품명': product.get('name', 'N/A'),
                        '가격': product.get('price', 'N/A'),
                        '판매자': product.get('seller', 'N/A'),
                        '소스': product.get('source', 'domeggook'),
                        '검색어': product.get('search_keyword', 'N/A')
                    })
                
                st.dataframe(display_results, use_container_width=True)
                
                if len(results) > 100:
                    st.info(f"⚠️ 결과가 많아 처음 100개만 표시합니다. 전체 {len(results)}개 결과는 저장된 파일에서 확인하세요.")
    
    except Exception as e:
        st.error(f"❌ 오류 발생: {str(e)}")
        logger.error(f"GUI 검색 오류: {e}", exc_info=True)
        st.session_state.search_running = False

def show_utility_tools():
    """유틸리티 도구 표시"""
    st.markdown('<div class="section-header">🛠️ 유틸리티 도구</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["JSON→CSV 변환", "CSV 병합", "파일에서 상품 등록"])
    
    with tab1:
        st.subheader("JSON → CSV 변환")
        st.write("result 폴더의 모든 JSON 파일을 CSV로 변환합니다.")
        
        overwrite = st.checkbox("기존 CSV 파일 덮어쓰기")
        
        if st.button("변환 시작", key="convert_btn"):
            with st.spinner("변환 중..."):
                count = convert_json_to_csv(result_dir=RESULT_DIR, overwrite=overwrite)
                st.success(f"✅ {count}개 파일 변환 완료!")
    
    with tab2:
        st.subheader("CSV 파일 병합")
        st.write("result 폴더의 모든 CSV 파일을 하나로 병합합니다.")
        
        add_keyword_col = st.checkbox("검색어 컬럼 추가", value=True)
        output_name = st.text_input("출력 파일명 (선택사항)", placeholder="merged_results.csv")
        
        if st.button("병합 시작", key="merge_btn"):
            with st.spinner("병합 중..."):
                output_file = merge_csv_files(
                    result_dir=RESULT_DIR,
                    output_file=output_name if output_name else None,
                    add_keyword_column=add_keyword_col
                )
                if output_file:
                    st.success(f"✅ 병합 완료! 파일: {output_file}")
                else:
                    st.error("❌ 병합 실패")
    
    with tab3:
        st.subheader("파일에서 상품 등록")
        st.write("검색 결과 파일에서 상품명을 추출하여 도매꾹에서 검색하고 마이박스에 등록합니다.")
        
        uploaded_file = st.file_uploader(
            "결과 파일 업로드 (CSV/JSON)",
            type=['csv', 'json']
        )
        
        max_products = st.number_input("최대 등록 상품 수", min_value=1, value=100)
        max_results_per_product = st.number_input("상품당 최대 검색 결과 수", min_value=1, value=5)
        min_price = st.number_input("최소 가격", min_value=0, value=DEFAULT_MIN_PRICE)
        
        username = st.text_input("아이디", value=get_username() or "")
        password = st.text_input("비밀번호", type="password", value="")
        if not password:
            password = get_password()
        
        headless = st.checkbox("헤드리스 모드", value=True)
        
        if st.button("등록 시작", key="register_btn") and uploaded_file:
            with st.spinner("등록 중..."):
                # 임시 파일로 저장
                with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_path = tmp_file.name
                
                try:
                    success = register_products_from_results(
                        results_file=tmp_path,
                        max_products=max_products,
                        max_results_per_product=max_results_per_product,
                        min_price=min_price if min_price > 0 else None,
                        username=username or None,
                        password=password or None,
                        headless=headless
                    )
                    
                    if success:
                        st.success("✅ 상품 등록 완료!")
                    else:
                        st.error("❌ 상품 등록 실패")
                finally:
                    os.unlink(tmp_path)

# 메인 실행
def main():
    # 사이드바 - 메뉴 선택
    menu = st.sidebar.selectbox(
        "메뉴",
        ["검색", "유틸리티"],
        index=0
    )
    
    if menu == "검색":
        run_search_with_gui()
    elif menu == "유틸리티":
        show_utility_tools()

if __name__ == "__main__":
    # 로거 설정
    setup_logger(level='INFO', log_file=None)
    main()

