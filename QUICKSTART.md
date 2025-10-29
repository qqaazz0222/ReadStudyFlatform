# 빠른 시작 가이드

이 가이드를 따라 5분 안에 CT Read Study Platform을 실행할 수 있습니다.

## 🎯 3단계로 시작하기

### 1️⃣ 프로젝트 준비

```bash
cd Read-Study-Platform
```

**Windows 사용자:**

```bash
quick_start.bat
```

**Linux/Mac 사용자:**

```bash
chmod +x quick_start.sh
./quick_start.sh
```

### 2️⃣ Conda 환경 생성 및 활성화

**방법 1: environment.yml 사용 (권장)**

```bash
conda env create -f environment.yml
conda activate read-study-platform
```

**방법 2: 수동 설치**

```bash
conda create -n read-study-platform python=3.10
conda activate read-study-platform
pip install -r requirements.txt
```

### 3️⃣ 샘플 데이터 생성 (선택사항)

실제 CT 데이터가 없다면 테스트용 샘플 데이터를 생성합니다:

```bash
python create_sample_data.py --num-patients 5
```

이 명령은 `data/ct_images/` 디렉토리에 5개의 샘플 환자 데이터를 생성합니다.

### 4️⃣ 플랫폼 실행

```bash
python main.py
```

브라우저에서 다음 주소로 접속:

```
http://localhost:7860
```

## 🔑 로그인 정보

-   **소속**: 아무거나 입력 (예: "서울대학교병원")
-   **성함**: 아무거나 입력 (예: "홍길동")
-   **비밀번호**: `dgu-plass-ct` (기본값)

## 📝 실제 데이터 사용하기

실제 CT 데이터를 사용하려면:

1. CT 볼륨을 Numpy 배열로 변환 (shape: `(z, y, x)`, dtype: `float32`)
2. HU 값으로 픽셀 값 설정
3. `.npy` 파일로 저장
4. `data/ct_images/` 디렉토리에 복사

예시 코드:

```python
import numpy as np

# CT 볼륨 데이터 (HU 값)
ct_volume = ...  # shape: (num_slices, height, width)

# 저장
np.save('data/ct_images/patient_001.npy', ct_volume)
```

## 🔧 설정 변경

`.env` 파일을 편집하여 설정을 변경할 수 있습니다:

-   `PORT`: 서버 포트 (기본값: 7860)
-   `CT_DATA_DIR`: CT 데이터 디렉토리 경로
-   `DATABASE_PATH`: 데이터베이스 파일 경로
-   `PLATFORM_PASSWORD_HASH`: 접속 비밀번호 해시값

### 비밀번호 변경 방법

```python
import hashlib
new_password = "새로운비밀번호"
hash_value = hashlib.sha256(new_password.encode()).hexdigest()
print(f"PLATFORM_PASSWORD_HASH={hash_value}")
```

출력된 값을 `.env` 파일의 `PLATFORM_PASSWORD_HASH`에 입력합니다.

## 💡 팁

### 성능 최적화

-   CT 데이터가 많은 경우, SSD에 저장하는 것을 권장합니다
-   메모리가 부족하면 한 번에 로드하는 환자 수를 제한할 수 있습니다

### 데이터 백업

```bash
# 데이터베이스 백업
cp database/read_study.db backups/read_study_$(date +%Y%m%d).db
```

### 로그 확인

터미널에서 실시간으로 로그를 확인할 수 있습니다.

## 🐛 문제 해결

### Port already in use 오류

다른 포트 사용:

```bash
# .env 파일에서
PORT=8080
```

### 모듈을 찾을 수 없음

Conda 환경이 활성화되었는지 확인:

```bash
conda info --envs
# 활성화된 환경 확인

# 환경 활성화
conda activate read-study-platform
```

의존성 재설치:

```bash
# environment.yml 사용 (권장)
conda env update -f environment.yml

# 또는 pip로 설치
pip install -r requirements.txt
```

### 환자 데이터를 로드할 수 없음

-   파일이 `.npy` 형식인지 확인
-   파일이 `data/ct_images/` 디렉토리에 있는지 확인
-   파일 권한 확인

## 📚 다음 단계

-   [README.md](README.md) - 전체 문서
-   [Description.md](Description.md) - 프로젝트 요구사항
-   코드 주석 확인 - 각 모듈의 상세 설명

## 🎓 사용 예시

1. **로그인**: 소속, 성함, 비밀번호 입력
2. **환자 선택**: 좌측 목록에서 환자 클릭
3. **영상 확인**: 슬라이스 및 윈도우 조절로 영상 탐색
4. **결과 제출**: CECT/sCECT 선택 후 제출
5. **다음 환자**: 다른 환자 선택하여 계속 분석

## ✅ 체크리스트

설치 전:

-   [ ] Anaconda 또는 Miniconda 설치 확인
-   [ ] Python 3.8 이상 버전 지원 확인

설치 후:

-   [ ] .env 파일 생성 확인
-   [ ] Conda 환경 생성 및 활성화 확인
-   [ ] 의존성 설치 완료
-   [ ] 샘플 데이터 생성 또는 실제 데이터 준비
-   [ ] 플랫폼 실행 성공

## 🆘 도움이 필요하신가요?

-   이슈 생성: GitHub Issues
-   문서 확인: README.md
-   코드 검토: 각 Python 파일의 docstring

---

**즐거운 연구 되세요! 🎉**
