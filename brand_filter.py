"""
브랜드 필터링 모듈
브랜드명을 제외하고 일반 키워드만 추출
"""
import re
from typing import List, Set, Dict
from collections import Counter

from logger import default_logger as logger

# 주요 브랜드명 리스트 (한국/해외 브랜드)
BRAND_KEYWORDS = {
    # 패션 브랜드
    '나이키', '아디다스', '퓨마', '뉴발란스', '컨버스', '반스',
    '자라', 'H&M', '유니클로', '무인양품', '지오다노', '스파오',
    '루이비통', '구찌', '샤넬', '프라다', '버버리', '에르메스',
    '아더에러', '룰루레몬', '파타고니아', '노스페이스', '컬럼비아',
    '아식스', '미즈노', '살로몬', '아크테릭스', '마몬트',
    
    # 전자제품 브랜드
    '아이폰', '갤럭시', '삼성', 'LG', '애플', '샤오미', '화웨이',
    '소니', '파나소닉', '캐논', '니콘', '고프로',
    '케이스티파이', '스피겐', '오터박스', '라인프렌즈',
    
    # 화장품 브랜드
    '라네즈', '설화수', '에뛰드', '더페이스샵', '이니스프리',
    '클리오', '에스티로더', '란콤', '디올', '샤넬', '맥',
    '네이처리퍼블릭', '토니모리', '미샤', '비오레',
    
    # 식품 브랜드
    '농심', '오리온', '롯데', '해태', '동원', 'CJ',
    '빼빼로', '초코파이', '새우깡', '포카칩',
    
    # 생활용품 브랜드
    '다이소', '이케아', '무인양품', '코스트코',
    '프로스펙스', '아식스', '미즈노',
    
    # 기타 유명 브랜드
    '스타벅스', '던킨도넛', '맥도날드', '버거킹',
    '테슬라', 'BMW', '벤츠', '아우디',
}

# 브랜드 패턴 (정규식)
BRAND_PATTERNS = [
    r'^[A-Z]{2,}$',  # 대문자만 (예: NIKE, ADIDAS)
    r'^[A-Z][a-z]+$',  # 첫 글자 대문자 (예: Apple, Samsung)
    r'.*브랜드.*',
    r'.*brand.*',
]

def is_brand_keyword(keyword: str) -> bool:
    """
    키워드가 브랜드명인지 판단
    
    Args:
        keyword: 확인할 키워드
    
    Returns:
        브랜드명이면 True, 아니면 False
    """
    if not keyword:
        return False
    
    keyword_lower = keyword.lower().strip()
    
    # 브랜드 리스트에 있는지 확인
    for brand in BRAND_KEYWORDS:
        if brand.lower() in keyword_lower or keyword_lower in brand.lower():
            return True
    
    # 브랜드 패턴 매칭
    for pattern in BRAND_PATTERNS:
        if re.match(pattern, keyword, re.IGNORECASE):
            return True
    
    # 특정 패턴 확인
    # 예: "나이키 러닝화" -> 나이키가 포함되어 있으면 브랜드
    for brand in BRAND_KEYWORDS:
        if brand in keyword:
            return True
    
    return False

def filter_brand_keywords(keywords: List[str]) -> List[str]:
    """
    브랜드 키워드를 제외하고 일반 키워드만 반환
    
    Args:
        keywords: 키워드 리스트
    
    Returns:
        브랜드가 제외된 키워드 리스트
    """
    filtered = []
    brands_found = []
    
    for keyword in keywords:
        if not is_brand_keyword(keyword):
            filtered.append(keyword)
        else:
            brands_found.append(keyword)
    
    if brands_found:
        logger.info(f"브랜드 키워드 제외: {', '.join(brands_found[:10])}")
        if len(brands_found) > 10:
            logger.info(f"... 외 {len(brands_found) - 10}개 브랜드 키워드 제외됨")
    
    return filtered

def analyze_competition(keywords: List[str], competition_data: Dict[str, Dict] = None) -> List[Dict]:
    """
    키워드별 경쟁 분석
    
    Args:
        keywords: 키워드 리스트
        competition_data: 경쟁 데이터 (검색수, 상품수, 경쟁강도 등)
    
    Returns:
        경쟁 분석 결과 리스트
    """
    results = []
    
    for keyword in keywords:
        analysis = {
            'keyword': keyword,
            'is_brand': is_brand_keyword(keyword),
            'competition_level': 'unknown',
            'recommendation': '',
        }
        
        # 경쟁 데이터가 있으면 분석
        if competition_data and keyword in competition_data:
            data = competition_data[keyword]
            search_count = data.get('search_count', 0)
            product_count = data.get('product_count', 0)
            competition_ratio = data.get('competition_ratio', 0)
            
            # 경쟁 강도 계산
            if product_count > 0:
                ratio = search_count / product_count
                if ratio > 10:
                    analysis['competition_level'] = 'low'  # 경쟁 낮음
                    analysis['recommendation'] = '추천'
                elif ratio > 5:
                    analysis['competition_level'] = 'medium'  # 경쟁 보통
                    analysis['recommendation'] = '보통'
                else:
                    analysis['competition_level'] = 'high'  # 경쟁 높음
                    analysis['recommendation'] = '주의'
            
            analysis.update(data)
        
        results.append(analysis)
    
    return results

def get_non_brand_keywords(keywords: List[str], min_length: int = 2) -> List[str]:
    """
    브랜드가 아닌 일반 키워드만 추출
    
    Args:
        keywords: 키워드 리스트
        min_length: 최소 키워드 길이
    
    Returns:
        일반 키워드 리스트
    """
    non_brand = []
    
    for keyword in keywords:
        keyword_clean = keyword.strip()
        
        # 최소 길이 확인
        if len(keyword_clean) < min_length:
            continue
        
        # 브랜드가 아닌 경우만 추가
        if not is_brand_keyword(keyword_clean):
            non_brand.append(keyword_clean)
    
    return non_brand

def extract_category_keywords(keyword: str) -> List[str]:
    """
    키워드에서 카테고리 키워드 추출
    
    예: "나이키 러닝화" -> ["러닝화"]
    예: "아이폰 케이스" -> ["케이스"]
    
    Args:
        keyword: 원본 키워드
    
    Returns:
        카테고리 키워드 리스트
    """
    # 브랜드명 제거
    words = keyword.split()
    category_words = []
    
    for word in words:
        if not is_brand_keyword(word):
            category_words.append(word)
    
    return category_words

