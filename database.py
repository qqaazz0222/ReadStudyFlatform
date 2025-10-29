"""
데이터베이스 모델 및 스키마 정의
SQLite3를 사용한 검사자 정보 및 분석 결과 관리
"""
import sqlite3
import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path
from config import config


class Database:
    """데이터베이스 관리 클래스"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE_PATH
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """데이터베이스 파일 및 테이블 생성"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 검사자 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inspectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                affiliation TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(affiliation, name)
            )
        """)
        
        # 분석 결과 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspector_id INTEGER NOT NULL,
                patient_id TEXT NOT NULL,
                result TEXT NOT NULL CHECK(result IN ('CECT', 'sCECT')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inspector_id) REFERENCES inspectors(id),
                UNIQUE(inspector_id, patient_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def get_or_create_inspector(self, affiliation: str, name: str) -> int:
        """검사자 정보 조회 또는 생성"""
        async with aiosqlite.connect(self.db_path) as db:
            # 기존 검사자 조회
            cursor = await db.execute(
                "SELECT id FROM inspectors WHERE affiliation = ? AND name = ?",
                (affiliation, name)
            )
            row = await cursor.fetchone()
            
            if row:
                # 마지막 로그인 시간 업데이트
                inspector_id = row[0]
                await db.execute(
                    "UPDATE inspectors SET last_login = ? WHERE id = ?",
                    (datetime.now(), inspector_id)
                )
                await db.commit()
                return inspector_id
            else:
                # 새 검사자 생성
                cursor = await db.execute(
                    "INSERT INTO inspectors (affiliation, name) VALUES (?, ?)",
                    (affiliation, name)
                )
                await db.commit()
                return cursor.lastrowid
    
    async def save_analysis_result(
        self,
        inspector_id: int,
        patient_id: str,
        result: str
    ) -> bool:
        """분석 결과 저장 또는 업데이트"""
        async with aiosqlite.connect(self.db_path) as db:
            # 기존 결과 확인
            cursor = await db.execute(
                "SELECT id FROM analysis_results WHERE inspector_id = ? AND patient_id = ?",
                (inspector_id, patient_id)
            )
            row = await cursor.fetchone()
            
            if row:
                # 기존 결과 업데이트
                await db.execute(
                    """UPDATE analysis_results 
                       SET result = ?, updated_at = ? 
                       WHERE inspector_id = ? AND patient_id = ?""",
                    (result, datetime.now(), inspector_id, patient_id)
                )
            else:
                # 새 결과 생성
                await db.execute(
                    """INSERT INTO analysis_results (inspector_id, patient_id, result)
                       VALUES (?, ?, ?)""",
                    (inspector_id, patient_id, result)
                )
            
            await db.commit()
            return True
    
    async def get_analysis_result(
        self,
        inspector_id: int,
        patient_id: str
    ) -> Optional[Dict]:
        """특정 환자에 대한 검사자의 분석 결과 조회"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT result, created_at, updated_at 
                   FROM analysis_results 
                   WHERE inspector_id = ? AND patient_id = ?""",
                (inspector_id, patient_id)
            )
            row = await cursor.fetchone()
            
            if row:
                return {
                    "result": row[0],
                    "created_at": row[1],
                    "updated_at": row[2]
                }
            return None
    
    async def get_inspector_results(self, inspector_id: int) -> List[Dict]:
        """검사자의 모든 분석 결과 조회"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT patient_id, result, created_at, updated_at 
                   FROM analysis_results 
                   WHERE inspector_id = ?
                   ORDER BY updated_at DESC""",
                (inspector_id,)
            )
            rows = await cursor.fetchall()
            
            return [
                {
                    "patient_id": row[0],
                    "result": row[1],
                    "created_at": row[2],
                    "updated_at": row[3]
                }
                for row in rows
            ]
    
    async def get_all_patient_results(self, patient_id: str) -> List[Dict]:
        """특정 환자에 대한 모든 검사자의 분석 결과 조회"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT i.affiliation, i.name, ar.result, ar.updated_at
                   FROM analysis_results ar
                   JOIN inspectors i ON ar.inspector_id = i.id
                   WHERE ar.patient_id = ?
                   ORDER BY ar.updated_at DESC""",
                (patient_id,)
            )
            rows = await cursor.fetchall()
            
            return [
                {
                    "affiliation": row[0],
                    "name": row[1],
                    "result": row[2],
                    "updated_at": row[3]
                }
                for row in rows
            ]


# 데이터베이스 인스턴스
db = Database()
