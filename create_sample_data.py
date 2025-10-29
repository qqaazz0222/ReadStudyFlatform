"""
샘플 CT 데이터 생성 유틸리티
테스트용 가짜 CT 볼륨 데이터를 생성합니다.
"""
import numpy as np
from pathlib import Path
import sys


def create_sample_ct_volume(
    num_slices=100,
    height=512,
    width=512,
    output_path=None
):
    """
    샘플 CT 볼륨 생성
    
    Args:
        num_slices: 슬라이스 수
        height: 이미지 높이
        width: 이미지 너비
        output_path: 저장할 경로
    """
    print(f"샘플 CT 볼륨 생성 중... (크기: {num_slices}x{height}x{width})")
    
    # 랜덤 시드 설정
    np.random.seed(42)
    
    # 기본 HU 값 범위: -1000 (공기) ~ 1000 (뼈)
    # 복부 영상을 시뮬레이션
    volume = np.zeros((num_slices, height, width), dtype=np.float32)
    
    for z in range(num_slices):
        # 배경 (공기): -1000 HU
        slice_img = np.full((height, width), -1000, dtype=np.float32)
        
        # 신체 영역 (타원형)
        center_y, center_x = height // 2, width // 2
        radius_y, radius_x = height // 3, width // 3
        
        y, x = np.ogrid[:height, :width]
        mask = ((y - center_y) ** 2 / radius_y ** 2 + 
                (x - center_x) ** 2 / radius_x ** 2) <= 1
        
        # 연조직: 20-60 HU
        slice_img[mask] = np.random.uniform(20, 60, slice_img[mask].shape)
        
        # 뼈 구조 추가 (척추)
        spine_x = center_x + int(radius_x * 0.6)
        spine_radius = 20
        spine_mask = ((y - center_y) ** 2 + (x - spine_x) ** 2) <= spine_radius ** 2
        slice_img[spine_mask] = np.random.uniform(400, 800, slice_img[spine_mask].shape)
        
        # 장기 추가 (간 시뮬레이션)
        if 30 <= z <= 70:
            organ_center_y = center_y - int(radius_y * 0.3)
            organ_center_x = center_x - int(radius_x * 0.3)
            organ_radius_y, organ_radius_x = 60, 80
            
            organ_mask = ((y - organ_center_y) ** 2 / organ_radius_y ** 2 + 
                         (x - organ_center_x) ** 2 / organ_radius_x ** 2) <= 1
            slice_img[organ_mask] = np.random.uniform(50, 70, slice_img[organ_mask].shape)
        
        # 노이즈 추가
        noise = np.random.normal(0, 10, (height, width))
        slice_img += noise
        
        volume[z] = slice_img
    
    # 저장
    if output_path:
        np.save(output_path, volume)
        print(f"✅ 저장 완료: {output_path}")
        print(f"   - Shape: {volume.shape}")
        print(f"   - HU Range: [{volume.min():.1f}, {volume.max():.1f}]")
        print(f"   - File Size: {Path(output_path).stat().st_size / (1024*1024):.2f} MB")
    
    return volume


def create_multiple_samples(num_patients=5, output_dir="./data/ct_images"):
    """
    여러 샘플 환자 데이터 생성
    
    Args:
        num_patients: 생성할 환자 수
        output_dir: 저장할 디렉토리
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print(f"🏥 {num_patients}명의 샘플 환자 CT 데이터 생성")
    print("=" * 60)
    print()
    
    for i in range(1, num_patients + 1):
        patient_id = f"patient_{i:03d}"
        file_path = output_path / f"{patient_id}.npy"
        
        print(f"[{i}/{num_patients}] {patient_id} 생성 중...")
        
        # 각 환자마다 약간 다른 크기로 생성
        num_slices = np.random.randint(80, 120)
        
        create_sample_ct_volume(
            num_slices=num_slices,
            height=512,
            width=512,
            output_path=file_path
        )
        print()
    
    print("=" * 60)
    print("✅ 모든 샘플 데이터 생성 완료!")
    print(f"📁 저장 위치: {output_path.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="CT Read Study Platform용 샘플 데이터 생성"
    )
    parser.add_argument(
        "--num-patients",
        type=int,
        default=5,
        help="생성할 환자 수 (기본값: 5)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./data/ct_images",
        help="저장할 디렉토리 (기본값: ./data/ct_images)"
    )
    
    args = parser.parse_args()
    
    create_multiple_samples(
        num_patients=args.num_patients,
        output_dir=args.output_dir
    )
