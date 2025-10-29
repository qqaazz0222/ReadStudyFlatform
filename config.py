"""
설정 파일 관리 모듈
.env 파일에서 환경 변수를 로드하고 관리합니다.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Config:
    """애플리케이션 설정 클래스"""
    
    # 보안 설정
    PLATFORM_PASSWORD_HASH = os.getenv(
        "PLATFORM_PASSWORD_HASH",
        "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92"
    )
    
    # 데이터베이스 설정
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./database/read_study.db")

    DATABASE_DIR = os.getenv("DATABASE_DIR", "./database/csv")

    # CT 영상 데이터 디렉토리
    CT_DATA_DIR = os.getenv("CT_DATA_DIR", "./data/ct_images")
    
    # 서버 설정
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "7860"))
    
    @classmethod
    def ensure_directories(cls):
        """필요한 디렉토리들이 존재하는지 확인하고 없으면 생성"""
        # 데이터베이스 디렉토리
        db_dir = Path(cls.DATABASE_PATH).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # CT 데이터 디렉토리
        ct_data_dir = Path(cls.CT_DATA_DIR)
        ct_data_dir.mkdir(parents=True, exist_ok=True)

# 설정 인스턴스
config = Config()
