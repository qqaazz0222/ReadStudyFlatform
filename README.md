# CT Read Study Platform

CT 영상 유효성 검증을 위한 리드 스터디 플랫폼입니다.

## 📋 개요

이 플랫폼은 생성된 CT 영상(sCECT)과 실제 조영증강 CT 영상(CECT)에 대한 유효성을 검증하기 위해 여러 의료진이 영상을 분석하고 결과를 제출할 수 있는 웹 기반 플랫폼입니다.

## 🚀 주요 기능

### 1. 인증 및 보안

-   SHA-256 암호화를 통한 비밀번호 검증
-   검사자 소속 및 성함 기반 세션 관리
-   비인가자 접속 차단

### 2. CT 영상 뷰어

-   Numpy 파일(.npy) 형식의 3D CT 볼륨 데이터 로딩
-   HU(Hounsfield Unit) 값 기반 윈도우 레벨/너비 조절
-   슬라이스별 영상 탐색
-   윈도우 프리셋 제공 (복부, 폐, 뼈, 뇌, 연조직)

### 3. 분석 결과 관리

-   CECT/sCECT 분류 결과 제출
-   검사자별 분석 결과 저장 및 조회
-   제출 이력 관리 (생성일시, 수정일시)
-   환자별 제출 상태 표시

## 📦 설치 방법

### 1. 저장소 클론

```bash
cd Read-Study-Platform
```

### 2. Conda 환경 생성 (권장)

```bash
conda env create -f environment.yml
conda activate read-study-platform
```

또는 기존 환경에 설치:

```bash
conda create -n read-study-platform python=3.10
conda activate read-study-platform
pip install -r requirements.txt
```

### 4. 환경 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성합니다:

```bash
cp .env.example .env
```

`.env` 파일을 편집하여 필요한 설정을 수정합니다:

```bash
# 플랫폼 접속 비밀번호 (SHA-256 해시값)
# 기본 비밀번호: "medical2024"
# 비밀번호 변경 시 Python에서 해시값 생성:
# python -c "import hashlib; print(hashlib.sha256('새비밀번호'.encode()).hexdigest())"
PLATFORM_PASSWORD_HASH=8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92

# 데이터베이스 경로
DATABASE_PATH=./database/read_study.db

# CT 영상 데이터 디렉토리
CT_DATA_DIR=./data/ct_images

# 서버 설정
HOST=0.0.0.0
PORT=7860
```

### 3. CT 데이터 준비

CT 영상 데이터를 `.npy` 형식으로 준비하여 `data/ct_images/` 디렉토리에 배치합니다:

```
data/ct_images/
├── patient_001.npy
├── patient_002.npy
└── patient_003.npy
```

**데이터 형식:**

-   Numpy 배열 형태: `(z, y, x)` - z는 슬라이스 수, y와 x는 이미지 크기
-   픽셀 값: HU(Hounsfield Unit) 값
-   파일명이 환자 ID로 사용됩니다

## 🎮 실행 방법

### 방법 1: Gradio UI 실행 (권장)

```bash
python main.py
```

브라우저에서 `http://localhost:7860` 접속

### 방법 2: FastAPI 백엔드만 실행

```bash
python api.py
```

API 문서: `http://localhost:7860/docs`

## 🖥️ 사용 방법

### 1. 로그인

1. 플랫폼에 접속하면 로그인 화면이 표시됩니다
2. 검사자의 **소속**과 **성함**을 입력합니다
3. **비밀번호**를 입력합니다 (기본값: `medical2024`)
4. **접속** 버튼을 클릭합니다

### 2. 환자 선택 및 영상 확인

1. 좌측 사이드바에서 환자를 선택합니다
    - ✅: 이미 분석 결과를 제출한 환자
    - ❌: 아직 분석 결과를 제출하지 않은 환자
2. 선택한 환자의 CT 영상이 중앙에 표시됩니다

### 3. 영상 조작

#### 슬라이스 조절

-   슬라이더를 움직여 다른 슬라이스를 확인합니다
-   또는 슬라이스 번호를 직접 입력합니다

#### 윈도우 조절

-   **윈도우 프리셋**: 자주 사용하는 윈도우 설정을 선택합니다
    -   복부(Abdomen): Level 40, Width 400
    -   폐(Lung): Level -600, Width 1500
    -   뼈(Bone): Level 400, Width 1800
    -   뇌(Brain): Level 40, Width 80
    -   연조직(Soft Tissue): Level 50, Width 350
-   **윈도우 레벨**: 중심 HU 값을 조절합니다 (-1000 ~ 1000)
-   **윈도우 너비**: 표시 범위를 조절합니다 (1 ~ 2000)

### 4. 분석 결과 제출

1. 영상을 충분히 확인한 후 결과를 선택합니다:
    - **CECT**: 실제 조영증강 CT 영상
    - **sCECT**: 생성된 조영증강 CT 영상
2. **결과 제출** 버튼을 클릭합니다
3. 제출 완료 메시지와 함께 환자 목록의 상태가 업데이트됩니다

### 5. 결과 수정

-   이미 제출한 환자를 다시 선택하면 이전 결과가 자동으로 표시됩니다
-   결과를 변경하고 다시 제출하면 업데이트됩니다
-   최종 제출 일시가 함께 표시됩니다

## 📁 프로젝트 구조

```
Read-Study-Platform/
├── main.py                 # 메인 실행 스크립트
├── app.py                  # Gradio UI 구현
├── api.py                  # FastAPI 백엔드 (선택적)
├── config.py               # 설정 관리
├── auth.py                 # 인증 및 보안
├── database.py             # 데이터베이스 모델
├── ct_utils.py             # CT 영상 처리 유틸리티
├── requirements.txt        # Python 의존성
├── .env.example            # 환경 변수 템플릿
├── .env                    # 환경 변수 (생성 필요)
├── README.md               # 이 파일
├── data/
│   └── ct_images/          # CT 영상 데이터 (.npy 파일)
└── database/
    └── read_study.db       # SQLite 데이터베이스 (자동 생성)
```

## 🔧 고급 설정

### 비밀번호 변경

새로운 비밀번호의 SHA-256 해시값을 생성합니다:

```python
import hashlib
password = "새비밀번호"
hash_value = hashlib.sha256(password.encode()).hexdigest()
print(hash_value)
```

생성된 해시값을 `.env` 파일의 `PLATFORM_PASSWORD_HASH`에 입력합니다.

### 포트 변경

`.env` 파일에서 `PORT` 값을 원하는 포트 번호로 변경합니다:

```bash
PORT=8080
```

### 데이터베이스 백업

```bash
cp database/read_study.db database/read_study.db.backup
```

## 📊 데이터베이스 스키마

### inspectors 테이블

검사자 정보를 저장합니다.

| 컬럼        | 타입      | 설명               |
| ----------- | --------- | ------------------ |
| id          | INTEGER   | 검사자 ID (기본키) |
| affiliation | TEXT      | 소속               |
| name        | TEXT      | 성함               |
| created_at  | TIMESTAMP | 생성 일시          |
| last_login  | TIMESTAMP | 마지막 로그인 일시 |

### analysis_results 테이블

분석 결과를 저장합니다.

| 컬럼         | 타입      | 설명                   |
| ------------ | --------- | ---------------------- |
| id           | INTEGER   | 결과 ID (기본키)       |
| inspector_id | INTEGER   | 검사자 ID (외래키)     |
| patient_id   | TEXT      | 환자 ID                |
| result       | TEXT      | 분석 결과 (CECT/sCECT) |
| created_at   | TIMESTAMP | 생성 일시              |
| updated_at   | TIMESTAMP | 수정 일시              |

## 🐛 문제 해결

### 1. 모듈을 찾을 수 없다는 오류

Conda 환경이 활성화되었는지 확인:

```bash
conda activate read-study-platform
```

의존성을 다시 설치:

```bash
# environment.yml 사용 (권장)
conda env update -f environment.yml

# 또는 pip로 설치
pip install -r requirements.txt
```

### 2. 환자 데이터를 로드할 수 없음

-   CT 데이터 파일이 올바른 디렉토리에 있는지 확인합니다
-   파일 형식이 `.npy`인지 확인합니다
-   파일 권한을 확인합니다

### 3. 비밀번호가 맞지 않음

-   `.env` 파일이 존재하는지 확인합니다
-   `PLATFORM_PASSWORD_HASH` 값이 올바른지 확인합니다
-   기본 비밀번호: `medical2024`

### 4. 포트가 이미 사용 중

-   `.env` 파일에서 다른 포트를 지정합니다
-   또는 실행 중인 프로세스를 종료합니다

## 📝 라이선스

이 프로젝트는 연구 목적으로 개발되었습니다.

## 👥 기여

버그 리포트 및 기능 제안은 이슈를 통해 제출해주세요.

## 📧 문의

프로젝트 관련 문의사항이 있으시면 이슈를 생성해주세요.
