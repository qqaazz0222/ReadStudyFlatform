"""
인증 및 보안 모듈
SHA-256 해싱을 통한 비밀번호 검증 기능
"""
import hashlib
from config import config


def hash_password(password: str) -> str:
    """
    비밀번호를 SHA-256으로 해싱
    
    Args:
        password: 평문 비밀번호
        
    Returns:
        SHA-256 해시값 (16진수 문자열)
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(password: str) -> bool:
    """
    입력된 비밀번호를 검증
    
    Args:
        password: 검증할 평문 비밀번호
        
    Returns:
        비밀번호가 올바르면 True, 아니면 False
    """
    hashed = hash_password(password)
    return hashed == config.PLATFORM_PASSWORD_HASH


def validate_inspector_info(affiliation: str, name: str, password: str) -> tuple[bool, str]:
    """
    검사자 정보 유효성 검증
    
    Args:
        affiliation: 소속
        name: 성함
        password: 비밀번호
        
    Returns:
        (검증 성공 여부, 오류 메시지)
    """
    # 필수 필드 검증
    if not affiliation or not affiliation.strip():
        return False, "소속을 입력해주세요."
    
    if not name or not name.strip():
        return False, "성함을 입력해주세요."
    
    if not password or not password.strip():
        return False, "비밀번호를 입력해주세요."
    
    # 비밀번호 검증
    if not verify_password(password):
        return False, "비밀번호가 올바르지 않습니다."
    
    return True, ""


class SessionManager:
    """세션 관리 클래스"""
    
    def __init__(self):
        self.current_inspector = None
        self.inspector_id = None
    
    def login(self, inspector_id: int, affiliation: str, name: str):
        """로그인 처리"""
        self.inspector_id = inspector_id
        self.current_inspector = {
            "id": inspector_id,
            "affiliation": affiliation,
            "name": name
        }
    
    def logout(self):
        """로그아웃 처리"""
        self.current_inspector = None
        self.inspector_id = None
    
    def is_authenticated(self) -> bool:
        """인증 상태 확인"""
        return self.current_inspector is not None
    
    def get_inspector_id(self) -> int:
        """현재 검사자 ID 반환"""
        return self.inspector_id if self.is_authenticated() else None
    
    def get_inspector_info(self) -> dict:
        """현재 검사자 정보 반환"""
        return self.current_inspector


# 세션 매니저 인스턴스
session = SessionManager()
