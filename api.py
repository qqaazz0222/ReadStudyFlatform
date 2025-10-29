"""
FastAPI 백엔드 API
인증, 환자 목록, 영상 데이터, 분석 결과 관리 API
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import base64
from io import BytesIO

from auth import validate_inspector_info, session
from database import db
from ct_utils import ct_processor, get_patient_list, WINDOW_PRESETS


# FastAPI 앱 생성
app = FastAPI(
    title="CT Read Study Platform API",
    description="CT 영상 유효성 검증을 위한 리드 스터디 플랫폼 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic 모델 정의
class LoginRequest(BaseModel):
    """로그인 요청 모델"""
    affiliation: str
    name: str
    password: str


class LoginResponse(BaseModel):
    """로그인 응답 모델"""
    success: bool
    message: str
    inspector_id: Optional[int] = None
    inspector_info: Optional[dict] = None


class AnalysisResultRequest(BaseModel):
    """분석 결과 제출 요청 모델"""
    patient_id: str
    result: str  # "CECT" or "sCECT"


class AnalysisResultResponse(BaseModel):
    """분석 결과 응답 모델"""
    success: bool
    message: str


class PatientListResponse(BaseModel):
    """환자 목록 응답 모델"""
    patients: List[str]
    submitted_patients: List[str]


class SliceImageRequest(BaseModel):
    """슬라이스 이미지 요청 모델"""
    patient_id: str
    slice_idx: int
    window_level: float = 40.0
    window_width: float = 400.0


# API 엔드포인트

@app.get("/")
async def root():
    """API 루트"""
    return {
        "message": "CT Read Study Platform API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    검사자 로그인
    
    소속, 성함, 비밀번호를 검증하고 세션 생성
    """
    # 입력 검증
    is_valid, error_msg = validate_inspector_info(
        request.affiliation,
        request.name,
        request.password
    )
    
    if not is_valid:
        return LoginResponse(
            success=False,
            message=error_msg
        )
    
    # 검사자 정보 생성 또는 조회
    inspector_id = await db.get_or_create_inspector(
        request.affiliation,
        request.name
    )
    
    # 세션 생성
    session.login(inspector_id, request.affiliation, request.name)
    
    return LoginResponse(
        success=True,
        message="로그인 성공",
        inspector_id=inspector_id,
        inspector_info={
            "affiliation": request.affiliation,
            "name": request.name
        }
    )


@app.post("/api/auth/logout")
async def logout():
    """로그아웃"""
    session.logout()
    return {"success": True, "message": "로그아웃 성공"}


@app.get("/api/auth/status")
async def auth_status():
    """인증 상태 확인"""
    is_authenticated = session.is_authenticated()
    return {
        "authenticated": is_authenticated,
        "inspector": session.get_inspector_info() if is_authenticated else None
    }


@app.get("/api/patients", response_model=PatientListResponse)
async def get_patients():
    """
    환자 목록 조회
    
    전체 환자 목록과 현재 검사자가 분석 결과를 제출한 환자 목록 반환
    """
    if not session.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다."
        )
    
    # 전체 환자 목록
    all_patients = get_patient_list()
    
    # 현재 검사자의 분석 결과 조회
    inspector_id = session.get_inspector_id()
    results = await db.get_inspector_results(inspector_id)
    submitted_patients = [r["patient_id"] for r in results]
    
    return PatientListResponse(
        patients=all_patients,
        submitted_patients=submitted_patients
    )


@app.get("/api/patient/{patient_id}/info")
async def get_patient_info(patient_id: str):
    """
    환자 볼륨 정보 조회
    
    환자 ID에 해당하는 CT 볼륨의 메타데이터 반환
    """
    if not session.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다."
        )
    
    # 볼륨 로드
    success = ct_processor.load_volume(patient_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"환자 데이터를 찾을 수 없습니다: {patient_id}"
        )
    
    # 볼륨 정보 반환
    info = ct_processor.get_volume_info()
    
    # 현재 검사자의 분석 결과 확인
    inspector_id = session.get_inspector_id()
    result = await db.get_analysis_result(inspector_id, patient_id)
    
    return {
        "volume_info": info,
        "analysis_result": result,
        "window_presets": WINDOW_PRESETS
    }


@app.post("/api/patient/slice")
async def get_patient_slice(request: SliceImageRequest):
    """
    환자의 특정 슬라이스 이미지 반환
    
    윈도우 레벨/너비를 적용한 슬라이스 이미지를 Base64로 인코딩하여 반환
    """
    if not session.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다."
        )
    
    # 현재 로드된 환자와 다른 경우 새로 로드
    if ct_processor.current_patient_id != request.patient_id:
        success = ct_processor.load_volume(request.patient_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"환자 데이터를 찾을 수 없습니다: {request.patient_id}"
            )
    
    # 슬라이스 이미지 생성
    pil_image = ct_processor.get_slice_as_pil(
        request.slice_idx,
        request.window_level,
        request.window_width
    )
    
    if pil_image is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 슬라이스 인덱스입니다."
        )
    
    # PIL Image를 Base64로 인코딩
    buffer = BytesIO()
    pil_image.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return {
        "image": f"data:image/png;base64,{img_base64}",
        "slice_idx": request.slice_idx,
        "window_level": request.window_level,
        "window_width": request.window_width
    }


@app.post("/api/analysis/submit", response_model=AnalysisResultResponse)
async def submit_analysis_result(request: AnalysisResultRequest):
    """
    분석 결과 제출
    
    현재 검사자의 특정 환자에 대한 분석 결과 저장
    """
    if not session.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다."
        )
    
    # 결과 유효성 검증
    if request.result not in ["CECT", "sCECT"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="결과는 'CECT' 또는 'sCECT'이어야 합니다."
        )
    
    # 분석 결과 저장
    inspector_id = session.get_inspector_id()
    success = await db.save_analysis_result(
        inspector_id,
        request.patient_id,
        request.result
    )
    
    if success:
        return AnalysisResultResponse(
            success=True,
            message="분석 결과가 성공적으로 제출되었습니다."
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="분석 결과 저장 중 오류가 발생했습니다."
        )


@app.get("/api/analysis/patient/{patient_id}")
async def get_patient_analysis_results(patient_id: str):
    """
    특정 환자에 대한 모든 검사자의 분석 결과 조회 (관리자용)
    """
    if not session.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다."
        )
    
    results = await db.get_all_patient_results(patient_id)
    
    return {
        "patient_id": patient_id,
        "results": results,
        "total_count": len(results)
    }


@app.get("/api/window-presets")
async def get_window_presets():
    """윈도우 프리셋 목록 조회"""
    return WINDOW_PRESETS


if __name__ == "__main__":
    import uvicorn
    from config import config
    
    # 필요한 디렉토리 생성
    config.ensure_directories()
    
    uvicorn.run(
        "api:app",
        host=config.HOST,
        port=config.PORT,
        reload=True
    )
