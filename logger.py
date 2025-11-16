"""
로깅 설정 모듈
"""
import logging
import os
from datetime import datetime
from typing import Optional

def setup_logger(
    name: str = "domeme",
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    로거 설정 및 반환
    
    Args:
        name: 로거 이름
        log_file: 로그 파일 경로 (None이면 파일 저장 안 함)
        level: 로그 레벨
        format_string: 로그 포맷 문자열
    
    Returns:
        설정된 로거 객체
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 이미 핸들러가 있으면 중복 추가 방지
    if logger.handlers:
        return logger
    
    # 기본 포맷 설정
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(format_string)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (선택사항)
    if log_file:
        # 로그 디렉토리 생성
        log_dir = os.path.dirname(log_file) if os.path.dirname(log_file) else '.'
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# 기본 로거 인스턴스 생성
default_logger = setup_logger()

