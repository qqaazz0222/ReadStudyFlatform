"""
CT 영상 처리 유틸리티
Numpy 파일 로딩, HU값 윈도우 조절, 슬라이스 추출 기능
"""
import numpy as np
from pathlib import Path
from typing import Tuple, List, Optional
import base64
from config import config


class CTImageProcessor:
    """CT 영상 처리 클래스"""
    
    def __init__(self):
        self.current_volume = None
        self.current_patient_id = None
        self.shape = None
    
    def load_volume(self, patient_id: str) -> bool:
        """
        환자의 CT 볼륨 데이터 로드
        
        Args:
            patient_id: 환자 ID (파일명)
            
        Returns:
            로드 성공 여부
        """
        try:
            file_path = Path(config.CT_DATA_DIR) / f"{patient_id}.npy"
            if not file_path.exists():
                return False
            
            self.current_volume = np.load(str(file_path))
            self.current_patient_id = patient_id
            self.shape = self.current_volume.shape
            return True
        except Exception as e:
            print(f"Error loading volume for {patient_id}: {e}")
            return False
    
    def get_slice(
        self,
        slice_idx: int,
        window_level: float = 40.0,
        window_width: float = 400.0
    ) -> Optional[np.ndarray]:
        """
        특정 슬라이스를 윈도우 조절하여 추출
        
        Args:
            slice_idx: 슬라이스 인덱스
            window_level: 윈도우 레벨 (HU)
            window_width: 윈도우 너비 (HU)
            
        Returns:
            윈도우 조절된 2D 이미지 배열 (0-255 범위)
        """
        if self.current_volume is None:
            return None
        
        if slice_idx < 0 or slice_idx >= self.shape[0]:
            return None
        
        # 슬라이스 추출 (z, y, x 순서)
        slice_data = self.current_volume[slice_idx, :, :]
        
        # 윈도우 조절 적용
        windowed = self.apply_window(slice_data, window_level, window_width)
        
        return windowed
    
    @staticmethod
    def apply_window(
        image: np.ndarray,
        window_level: float,
        window_width: float
    ) -> np.ndarray:
        """
        HU 값에 윈도우 레벨/너비 적용
        
        Args:
            image: HU 값으로 이루어진 2D 배열
            window_level: 윈도우 레벨 (중심값)
            window_width: 윈도우 너비
            
        Returns:
            0-255 범위로 스케일된 이미지
        """
        # 윈도우 범위 계산
        window_min = window_level - (window_width / 2)
        window_max = window_level + (window_width / 2)
        
        # 윈도우 적용 및 클리핑
        windowed = np.clip(image, window_min, window_max)
        
        # 0-255 범위로 정규화
        windowed = ((windowed - window_min) / (window_max - window_min) * 255.0)
        windowed = windowed.astype(np.uint8)
        
        return windowed
    
    def get_slice_as_base64(
        self,
        slice_idx: int,
        window_level: float = 40.0,
        window_width: float = 400.0
    ) -> Optional[str]:
        """
        특정 슬라이스를 Base64 인코딩된 RGB 바이너리 데이터로 반환
        
        Args:
            slice_idx: 슬라이스 인덱스
            window_level: 윈도우 레벨 (HU)
            window_width: 윈도우 너비 (HU)
            
        Returns:
            Base64 인코딩된 RGB 이미지 데이터 (또는 None)
        """
        slice_array = self.get_slice(slice_idx, window_level, window_width)
        
        if slice_array is None:
            return None
        
        # 그레이스케일을 RGB로 변환 (각 픽셀을 3번 반복)
        # shape: (height, width) -> (height, width, 3)
        rgb_array = np.stack([slice_array, slice_array, slice_array], axis=-1)
        
        # C-contiguous 형태로 변환 후 바이트로 변환
        rgb_bytes = np.ascontiguousarray(rgb_array).tobytes('C')
        
        # Base64 인코딩
        return base64.b64encode(rgb_bytes).decode('utf-8')
    
    def get_volume_info(self) -> Optional[dict]:
        """
        현재 로드된 볼륨의 정보 반환
        
        Returns:
            볼륨 정보 딕셔너리
        """
        if self.current_volume is None:
            return None
        
        return {
            "patient_id": self.current_patient_id,
            "shape": self.shape,
            "num_slices": self.shape[0],
            "height": self.shape[1],
            "width": self.shape[2],
            "min_hu": float(np.min(self.current_volume)),
            "max_hu": float(np.max(self.current_volume)),
            "mean_hu": float(np.mean(self.current_volume))
        }
    
    def clear(self):
        """현재 로드된 볼륨 메모리에서 제거"""
        self.current_volume = None
        self.current_patient_id = None
        self.shape = None


def get_patient_list() -> List[str]:
    """
    CT 데이터 디렉토리에서 환자 목록 추출
    
    Returns:
        환자 ID 리스트 (.npy 파일명에서 확장자 제거)
    """
    ct_dir = Path(config.CT_DATA_DIR)
    if not ct_dir.exists():
        return []
    
    patient_files = sorted(ct_dir.glob("*.npy"))
    return [f.stem for f in patient_files]


# 윈도우 프리셋 정의
WINDOW_PRESETS = {
    "복부(Abdomen)": {"level": 40, "width": 400},
    "폐(Lung)": {"level": -600, "width": 1500},
    "뼈(Bone)": {"level": 400, "width": 1800},
    "뇌(Brain)": {"level": 40, "width": 80},
    "연조직(Soft Tissue)": {"level": 50, "width": 350},
}


# CT 이미지 프로세서 인스턴스
ct_processor = CTImageProcessor()
