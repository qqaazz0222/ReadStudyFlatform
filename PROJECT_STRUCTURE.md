# CT Read Study Platform - 프로젝트 구조

## 📁 파일 구조

```
Read-Study-Platform/
│
├── 📝 문서
│   ├── README.md                # 전체 프로젝트 문서
│   ├── QUICKSTART.md            # 빠른 시작 가이드
│   └── Description.md           # 프로젝트 요구사항 명세
│
├── 🚀 실행 스크립트
│   ├── main.py                  # 메인 실행 파일
│   ├── quick_start.sh           # Linux/Mac 빠른 시작 스크립트
│   └── quick_start.bat          # Windows 빠른 시작 스크립트
│
├── 🎨 프론트엔드 (Gradio UI)
│   └── app.py                   # Gradio 웹 인터페이스
│
├── ⚙️ 백엔드 (FastAPI - 선택사항)
│   └── api.py                   # REST API 서버
│
├── 🔧 핵심 모듈
│   ├── config.py                # 설정 관리
│   ├── auth.py                  # 인증 및 보안
│   ├── database.py              # 데이터베이스 모델 및 쿼리
│   └── ct_utils.py              # CT 영상 처리 유틸리티
│
├── 🛠️ 유틸리티
│   └── create_sample_data.py    # 샘플 데이터 생성 도구
│
├── ⚙️ 설정 파일
│   ├── environment.yml          # Conda 환경 설정 (권장)
│   ├── requirements.txt         # Python 의존성 (pip)
│   ├── .env.example             # 환경 변수 템플릿
│   ├── .env                     # 환경 변수 (생성 필요)
│   └── .gitignore               # Git 무시 파일
│
├── 💾 데이터 (자동 생성)
│   ├── data/
│   │   └── ct_images/           # CT 영상 데이터 (.npy 파일)
│   └── database/
│       └── read_study.db        # SQLite 데이터베이스
│
└── 🐍 Conda 환경 (생성 권장)
    └── read-study-platform/     # Conda 환경
```

## 🔑 핵심 파일 설명

### 1. main.py

-   **목적**: 플랫폼의 진입점
-   **기능**: Gradio UI 실행, 초기 설정
-   **사용법**: `python main.py`

### 2. app.py

-   **목적**: 사용자 인터페이스
-   **기능**: 로그인, 영상 뷰어, 결과 제출
-   **기술**: Gradio
-   **주요 컴포넌트**:
    -   로그인 페이지
    -   환자 목록 사이드바
    -   CT 영상 뷰어
    -   슬라이스/윈도우 조절
    -   결과 제출 폼

### 3. api.py (선택사항)

-   **목적**: RESTful API 서버
-   **기능**: HTTP API 엔드포인트
-   **기술**: FastAPI
-   **사용 시나리오**:
    -   다른 시스템과 연동
    -   프로그래밍 방식 접근
    -   API 문서 자동 생성

### 4. config.py

-   **목적**: 중앙 설정 관리
-   **내용**:
    -   데이터베이스 경로
    -   CT 데이터 디렉토리
    -   서버 호스트/포트
    -   비밀번호 해시
-   **환경 변수**: `.env` 파일에서 로드

### 5. auth.py

-   **목적**: 인증 및 보안
-   **기능**:
    -   SHA-256 비밀번호 해싱
    -   비밀번호 검증
    -   세션 관리
    -   검사자 정보 유효성 검증

### 6. database.py

-   **목적**: 데이터베이스 관리
-   **기능**:
    -   SQLite3 연결 관리
    -   검사자 CRUD
    -   분석 결과 CRUD
-   **테이블**:
    -   `inspectors`: 검사자 정보
    -   `analysis_results`: 분석 결과

### 7. ct_utils.py

-   **목적**: CT 영상 처리
-   **기능**:
    -   Numpy 파일 로딩
    -   HU 값 윈도우 조절
    -   슬라이스 추출
    -   PIL Image 변환
-   **윈도우 프리셋**: 복부, 폐, 뼈, 뇌, 연조직

### 8. create_sample_data.py

-   **목적**: 테스트 데이터 생성
-   **기능**: 가짜 CT 볼륨 생성
-   **사용법**: `python create_sample_data.py --num-patients 5`

## 🔄 데이터 흐름

```
1. 사용자 로그인
   ↓
   app.py → auth.py → database.py
   ↓
2. 환자 선택
   ↓
   app.py → ct_utils.py (볼륨 로드)
   ↓
3. 영상 조작
   ↓
   app.py → ct_utils.py (슬라이스/윈도우 조절)
   ↓
4. 결과 제출
   ↓
   app.py → database.py (결과 저장)
```

## 🗄️ 데이터베이스 스키마

### inspectors 테이블

```sql
CREATE TABLE inspectors (
    id INTEGER PRIMARY KEY,
    affiliation TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP,
    last_login TIMESTAMP,
    UNIQUE(affiliation, name)
);
```

### analysis_results 테이블

```sql
CREATE TABLE analysis_results (
    id INTEGER PRIMARY KEY,
    inspector_id INTEGER,
    patient_id TEXT NOT NULL,
    result TEXT CHECK(result IN ('CECT', 'sCECT')),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (inspector_id) REFERENCES inspectors(id),
    UNIQUE(inspector_id, patient_id)
);
```

## 🎯 핵심 기능 흐름

### 로그인 프로세스

1. 사용자가 소속, 성함, 비밀번호 입력
2. `auth.validate_inspector_info()`: 입력 검증
3. `auth.verify_password()`: SHA-256 해시 비교
4. `database.get_or_create_inspector()`: 검사자 조회/생성
5. `session.login()`: 세션 생성
6. 뷰어 페이지로 전환

### CT 영상 로딩

1. 사용자가 환자 선택
2. `ct_processor.load_volume()`: .npy 파일 로드
3. `ct_processor.get_volume_info()`: 메타데이터 추출
4. `database.get_analysis_result()`: 이전 결과 조회
5. 첫 슬라이스 표시

### 영상 조작

1. 슬라이더/숫자 입력으로 값 변경
2. `ct_processor.get_slice()`: HU 데이터 추출
3. `ct_processor.apply_window()`: 윈도우 적용
4. `ct_processor.get_slice_as_pil()`: PIL Image 변환
5. Gradio에 이미지 표시

### 결과 제출

1. 사용자가 CECT/sCECT 선택
2. 결과 제출 버튼 클릭
3. `database.save_analysis_result()`: DB에 저장
4. 환자 목록 상태 업데이트 (✅ 표시)

## 🔐 보안 요소

1. **비밀번호 해싱**: SHA-256
2. **세션 관리**: 메모리 기반 세션
3. **입력 검증**: 모든 사용자 입력 검증
4. **SQL 인젝션 방지**: 파라미터화된 쿼리

## 📊 성능 고려사항

1. **메모리 관리**:

    - 한 번에 하나의 볼륨만 로드
    - 환자 변경 시 이전 볼륨 해제

2. **파일 I/O**:

    - Numpy 파일 로딩 캐싱
    - 슬라이스 단위 처리

3. **데이터베이스**:
    - SQLite 인덱스 활용
    - Async 쿼리 (aiosqlite)

## 🧪 테스트 시나리오

1. **Conda 환경 설정**

    ```bash
    conda env create -f environment.yml
    conda activate read-study-platform
    ```

2. **샘플 데이터 생성**

    ```bash
    python create_sample_data.py --num-patients 3
    ```

3. **플랫폼 실행**

    ```bash
    python main.py
    ```

4. **기능 테스트**
    - [ ] 로그인 성공/실패
    - [ ] 환자 목록 표시
    - [ ] 환자 선택 및 영상 로딩
    - [ ] 슬라이스 조절
    - [ ] 윈도우 조절
    - [ ] 프리셋 적용
    - [ ] 결과 제출
    - [ ] 결과 수정
    - [ ] 로그아웃

## 🔄 확장 가능성

### 현재 구현

-   ✅ Gradio UI
-   ✅ SQLite 데이터베이스
-   ✅ 로컬 파일 저장
-   ✅ 단일 서버

### 향후 확장

-   🔮 PostgreSQL/MySQL 지원
-   🔮 클라우드 스토리지 (S3, GCS)
-   🔮 멀티 유저 동시 접속
-   🔮 DICOM 파일 직접 지원
-   🔮 3D 볼륨 렌더링
-   🔮 통계 대시보드
-   🔮 결과 내보내기 (CSV, Excel)

## 📚 추가 자료

-   [Conda 문서](https://docs.conda.io/)
-   [Gradio 문서](https://www.gradio.app/docs/)
-   [FastAPI 문서](https://fastapi.tiangolo.com/)
-   [NumPy 문서](https://numpy.org/doc/)
-   [Pillow 문서](https://pillow.readthedocs.io/)
-   [SQLite 문서](https://www.sqlite.org/docs.html)

---

**이 문서는 프로젝트 구조와 핵심 개념을 이해하기 위한 참고 자료입니다.**
