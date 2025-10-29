"""
데이터베이스 분석 결과를 CSV 파일로 내보내기
환자 ID를 행으로, 검사자 정보를 열로 하는 매트릭스 형태로 저장
"""
import os
import sqlite3
import csv
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set
from config import config
from ct_utils import get_patient_list


async def export_results_to_csv(output_path: str = None):
    """
    데이터베이스의 모든 분석 결과를 CSV 파일로 내보내기
    
    Args:
        output_path: CSV 파일 저장 경로 (기본값: database/results_YYYYMMDD_HHMMSS.csv)
    """
    # 출력 파일 경로 설정
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(config.DATABASE_DIR) / f"results_{timestamp}.csv"
        os.makedirs(config.DATABASE_DIR, exist_ok=True)
    else:
        output_path = Path(output_path)
    
    # 데이터베이스에서 모든 데이터 조회
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 모든 검사자 정보 조회
    cursor.execute("""
        SELECT id, affiliation, name 
        FROM inspectors 
        ORDER BY affiliation, name
    """)
    inspectors = cursor.fetchall()
    
    # 모든 분석 결과 조회
    cursor.execute("""
        SELECT inspector_id, patient_id, result, updated_at
        FROM analysis_results
        ORDER BY patient_id, inspector_id
    """)
    results = cursor.fetchall()
    
    conn.close()
    
    # 데이터 구조화
    # 검사자 정보를 컬럼으로 사용
    inspector_map = {}
    column_headers = ["Patient_ID"]
    
    for inspector in inspectors:
        inspector_id = inspector['id']
        inspector_label = f"{inspector['affiliation']}_{inspector['name']}"
        inspector_map[inspector_id] = inspector_label
        column_headers.append(inspector_label)
    
    # 환자 목록 가져오기 (데이터 폴더에 있는 모든 환자)
    all_patients = get_patient_list()
    
    # 결과 데이터를 딕셔너리로 변환
    result_dict = {}
    for result in results:
        patient_id = result['patient_id']
        inspector_id = result['inspector_id']
        value = result['result']
        
        if patient_id not in result_dict:
            result_dict[patient_id] = {}
        
        inspector_label = inspector_map.get(inspector_id, f"Inspector_{inspector_id}")
        result_dict[patient_id][inspector_label] = value
    
    # CSV 파일 작성
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # 헤더 작성
        writer.writerow(column_headers)
        
        # 각 환자에 대한 행 작성
        for patient_id in sorted(all_patients):
            row = [patient_id]
            
            # 각 검사자의 결과 추가 (없으면 빈 문자열)
            for inspector_label in column_headers[1:]:
                if patient_id in result_dict:
                    value = result_dict[patient_id].get(inspector_label, '')
                else:
                    value = ''
                row.append(value)
            
            writer.writerow(row)
    
    print(f"✅ CSV 파일이 생성되었습니다: {output_path}")
    print(f"   - 환자 수: {len(all_patients)}")
    print(f"   - 검사자 수: {len(inspectors)}")
    print(f"   - 총 분석 결과 수: {len(results)}")
    
    return str(output_path)


async def export_summary_statistics(output_path: str = None):
    """
    분석 결과 통계를 CSV 파일로 내보내기
    
    Args:
        output_path: CSV 파일 저장 경로 (기본값: database/statistics_YYYYMMDD_HHMMSS.csv)
    """
    # 출력 파일 경로 설정
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(config.DATABASE_DIR) / f"statistics_{timestamp}.csv"
    else:
        output_path = Path(output_path)
    
    # 데이터베이스에서 통계 정보 조회
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 각 검사자별 통계
    cursor.execute("""
        SELECT 
            i.affiliation,
            i.name,
            COUNT(*) as total_analyzed,
            SUM(CASE WHEN ar.result = 'CECT' THEN 1 ELSE 0 END) as cect_count,
            SUM(CASE WHEN ar.result = 'sCECT' THEN 1 ELSE 0 END) as scect_count,
            MIN(ar.created_at) as first_analysis,
            MAX(ar.updated_at) as last_analysis
        FROM inspectors i
        LEFT JOIN analysis_results ar ON i.id = ar.inspector_id
        GROUP BY i.id, i.affiliation, i.name
        ORDER BY i.affiliation, i.name
    """)
    
    statistics = cursor.fetchall()
    conn.close()
    
    # CSV 파일 작성
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # 헤더 작성
        writer.writerow([
            'Affiliation',
            'Name',
            'Total_Analyzed',
            'CECT_Count',
            'sCECT_Count',
            'CECT_Percentage',
            'First_Analysis',
            'Last_Analysis'
        ])
        
        # 각 검사자별 통계 작성
        for stat in statistics:
            total = stat['total_analyzed'] or 0
            cect = stat['cect_count'] or 0
            scect = stat['scect_count'] or 0
            cect_pct = (cect / total * 100) if total > 0 else 0
            
            writer.writerow([
                stat['affiliation'],
                stat['name'],
                total,
                cect,
                scect,
                f"{cect_pct:.1f}%",
                stat['first_analysis'] or '',
                stat['last_analysis'] or ''
            ])
    
    print(f"✅ 통계 CSV 파일이 생성되었습니다: {output_path}")
    print(f"   - 검사자 수: {len(statistics)}")
    
    return str(output_path)


async def export_with_timestamps(output_path: str = None):
    """
    분석 결과를 타임스탬프와 함께 CSV 파일로 내보내기
    각 검사자-환자 조합마다 결과와 업데이트 시간을 저장
    
    Args:
        output_path: CSV 파일 저장 경로 (기본값: database/results_with_time_YYYYMMDD_HHMMSS.csv)
    """
    # 출력 파일 경로 설정
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(config.DATABASE_DIR) / f"results_with_time_{timestamp}.csv"
    else:
        output_path = Path(output_path)
    
    # 데이터베이스에서 모든 데이터 조회
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            i.affiliation,
            i.name,
            ar.patient_id,
            ar.result,
            ar.created_at,
            ar.updated_at
        FROM analysis_results ar
        JOIN inspectors i ON ar.inspector_id = i.id
        ORDER BY ar.patient_id, i.affiliation, i.name
    """)
    
    results = cursor.fetchall()
    conn.close()
    
    # CSV 파일 작성
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # 헤더 작성
        writer.writerow([
            'Patient_ID',
            'Affiliation',
            'Inspector_Name',
            'Result',
            'Created_At',
            'Updated_At'
        ])
        
        # 각 결과 작성
        for result in results:
            writer.writerow([
                result['patient_id'],
                result['affiliation'],
                result['name'],
                result['result'],
                result['created_at'],
                result['updated_at']
            ])
    
    print(f"✅ 타임스탬프 포함 CSV 파일이 생성되었습니다: {output_path}")
    print(f"   - 총 분석 결과 수: {len(results)}")
    
    return str(output_path)


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='데이터베이스 분석 결과를 CSV 파일로 내보내기')
    parser.add_argument(
        '--type',
        choices=['matrix', 'statistics', 'timestamp', 'all'],
        default='all',
        help='내보낼 CSV 타입 (기본값: all)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='출력 CSV 파일 경로 (기본값: database/results_*.csv)'
    )
    
    args = parser.parse_args()
    
    async def run_export():
        if args.type in ['matrix', 'all']:
            await export_results_to_csv(args.output)
            print()
        
        if args.type in ['statistics', 'all']:
            await export_summary_statistics()
            print()
        
        if args.type in ['timestamp', 'all']:
            await export_with_timestamps()
            print()
    
    # 비동기 함수 실행
    asyncio.run(run_export())


if __name__ == "__main__":
    main()
