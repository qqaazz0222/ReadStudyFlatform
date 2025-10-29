"""
CT Read Study Platform - Main Entry Point
메인 실행 스크립트
"""
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from app import create_ui


def main():
    """메인 함수"""
    print("=" * 60)
    print("🏥 CT Read Study Platform")
    print("=" * 60)
    print(f"📍 Server: http://{config.HOST}:{config.PORT}")
    print(f"📁 CT Data Directory: {config.CT_DATA_DIR}")
    print(f"💾 Database: {config.DATABASE_PATH}")
    print("=" * 60)
    print()
    
    # 필요한 디렉토리 생성
    config.ensure_directories()
    
    # Gradio UI 생성 및 실행
    app = create_ui()
    
    app.launch(
        server_name=config.HOST,
        server_port=config.PORT,
        share=False,
        show_error=True,
        quiet=False
    )


if __name__ == "__main__":
    main()
