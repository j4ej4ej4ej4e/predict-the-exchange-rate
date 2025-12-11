# predict-the-exchange-rate
다변량 시계열 모델을 활용해 환율을 예측합니다.  
# 🌍 USD/KRW 환율 예측 시스템

> 딥러닝 기반 다변량 시계열 분석을 활용한 여행자 대상 최적 환전 시점 예측 시스템

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.13+-orange.svg)](https://www.tensorflow.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📋 목차

- [프로젝트 소개](#프로젝트-소개)
- [주요 기능](#주요-기능)
- [시스템 아키텍처](#시스템-아키텍처)
- [기술 스택](#기술-스택)
- [설치 방법](#설치-방법)
- [사용 방법](#사용-방법)
- [모델 성능](#모델-성능)
- [디렉토리 구조](#디렉토리-구조)
- [라이선스](#라이선스)

## 🎯 프로젝트 소개

이 프로젝트는 **Bi-LSTM (Bidirectional Long Short-Term Memory)** 딥러닝 모델을 활용하여 USD/KRW 환율을 예측하고, 여행자에게 최적의 환전 시점을 추천하는 시스템입니다.

### 핵심 특징

- 📊 **15개의 다변량 거시경제 지표** 활용
- 🤖 **Bi-LSTM 모델**로 7일 후 환율 예측
- 🔄 **자동화 파이프라인**: Windows 작업 스케줄러로 4일마다 자동 실행
- 🔥 **Firebase 연동**: 예측 결과 실시간 저장
- 🌐 **웹 대시보드**: 직관적인 예측 결과 시각화

### 성능 지표

- **RMSE**: 17.82원
- **R² Score**: 0.7961
- **데이터 기간**: 2010년 ~ 현재 (약 3,900일)
- **예측 기간**: 7일

## ✨ 주요 기능

### 1. 자동 데이터 수집
- Yahoo Finance API: 주식, 상품 가격
- FRED API: 금리, 경제 지표
- MySQL 데이터베이스 자동 저장

### 2. 전처리 파이프라인
- Wavelet 노이즈 제거
- 기술적 지표 계산 (MA, RSI, Bollinger Bands)
- 정규화 및 슬라이딩 윈도우 생성

### 3. 딥러닝 모델
- **Bi-LSTM (2-Stack)** 아키텍처
- Attention Mechanism
- Dropout & Batch Normalization

### 4. 자동화 스케줄러
- **Windows 작업 스케줄러**: 4일마다 자동 실행
- Papermill: Jupyter Notebook 자동화
- Firebase: 예측 결과 자동 업로드

### 5. 웹 대시보드
- 미래 7일 환율 예측 차트
- 최적 환전 시점 AI 추천
- 모델 성능 시각화

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐
│ Yahoo Finance   │
│ FRED API        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Data Collection │ (2data_get.py)
│ + Preprocessing │ (3data_preprocess.py)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  MySQL Database │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Bi-LSTM Model  │ (3train.ipynb)
│   Training      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Firebase        │
│ Firestore       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Web Dashboard   │ (dashboard_v2.html)
│ (HTML/JS)       │
└─────────────────┘
```

### 자동화 파이프라인

```
Windows 작업 스케줄러 (매 4일)
    ↓
scheduler.py
    ↓
2data_get.py (데이터 수집)
    ↓
3data_preprocess.py (전처리)
    ↓
3train.ipynb (모델 훈련)
    ↓
Firebase (결과 저장)
```

## 🛠️ 기술 스택

### Backend & ML
- **Python 3.8+**
- **TensorFlow 2.13+** - 딥러닝 모델
- **Scikit-learn** - 전처리 및 평가
- **PyWavelets** - 신호 처리
- **MySQL** - 데이터베이스
- **Windows 작업 스케줄러** - 자동화
- **Papermill** - Notebook 자동화

### Data Source
- **yfinance** - Yahoo Finance API
- **fredapi** - FRED 경제 지표

### Cloud & Storage
- **Firebase Firestore** - NoSQL 데이터베이스
- **Firebase Storage** - 모델 파일 저장

### Frontend
- **HTML/CSS/JavaScript**
- **Chart.js** - 데이터 시각화

## 📦 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/yourusername/usd-krw-exchange-prediction.git
cd usd-krw-exchange-prediction
```

### 2. 가상환경 생성 (권장)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 설정

#### MySQL 설정
```sql
CREATE DATABASE exchangeDATAbase;
CREATE TABLE raw_macro_data (
    date DATE PRIMARY KEY,
    usd_krw FLOAT,
    wti_price FLOAT,
    sp500_index FLOAT,
    -- ... (기타 컬럼)
);
```

#### Firebase 설정
1. [Firebase Console](https://console.firebase.google.com/) 접속
2. 프로젝트 생성
3. Firestore Database 활성화 (asia-northeast3 권장)
4. 서비스 계정 키 다운로드 → `firebase-key.json`으로 저장

#### API 키 설정
```python
# 2data_get.py 수정
FRED_API_KEY = "your_fred_api_key_here"

# firebase_config.py 수정
cred = credentials.Certificate("firebase-key.json")
```

## 🚀 사용 방법

### 개별 실행

#### 1단계: 데이터 수집
```bash
python 2data_get.py
```

#### 2단계: 데이터 전처리
```bash
python 3data_preprocess.py
```

#### 3단계: 모델 훈련
```bash
jupyter notebook 3train.ipynb
# 또는
papermill 3train.ipynb output.ipynb
```

### 자동화 실행

#### 테스트 실행 (한 번만)
```bash
python scheduler.py once
```

#### Windows 작업 스케줄러 등록

**방법 1: GUI (추천)**
1. Windows 검색 → "작업 스케줄러" 실행
2. "기본 작업 만들기" 클릭
3. 이름: `USD/KRW 환율 예측 모델 훈련`
4. 트리거: 매일, 새벽 3시, 4일 간격 반복
5. 작업: 프로그램 시작
   - 프로그램: `python`
   - 인수: `scheduler.py`
   - 시작 위치: `프로젝트 폴더 경로`

**상세 가이드**: [WINDOWS_SCHEDULER_GUIDE.md](WINDOWS_SCHEDULER_GUIDE.md) 참조

### 웹 대시보드

1. `dashboard_v2.html` 파일을 브라우저로 열기
2. 현재 환율 입력
3. 출국일 선택
4. **[최적 환전 시점 추천 받기]** 버튼 클릭

## 📊 모델 성능

### 성능 지표

| Metric | Value |
|--------|-------|
| RMSE | 17.82원 |
| R² Score | 0.7961 |
| MAE | 13.45원 |
| Training Time | ~5분 |

### 사용 Features (15개)

| Category | Features |
|----------|----------|
| **환율** | USD/KRW, USD/JPY, USD/CNY, EUR/USD |
| **상품** | WTI 유가, 금 가격, DXY 달러 인덱스 |
| **주식** | S&P 500, KOSPI, VIX (공포지수) |
| **금리** | 미국 금리, 한국 금리, 금리차(IRD), 장단기 스프레드 |
| **변동성** | KOSPI 변동성 |

### 모델 아키텍처

```
Input (60, 15)
    ↓
Bi-LSTM (64 units) + Dropout(0.2)
    ↓
Bi-LSTM (32 units) + Dropout(0.2)
    ↓
Dense (16 units, ReLU)
    ↓
Dense (1 unit, Linear) → Output
```

## 📂 디렉토리 구조

```
usd-krw-exchange-prediction/
│
├── 2data_get.py                # 데이터 수집 스크립트
├── 3data_preprocess.py          # 데이터 전처리
├── 3model.py                    # 모델 아키텍처 정의
├── 3train.ipynb                 # 모델 훈련 노트북
│
├── scheduler.py                 # 자동화 스케줄러 (Windows용)
├── firebase_config.py           # Firebase 설정
├── dashboard_v2.html            # 웹 대시보드
│
├── requirements.txt             # Python 패키지 목록
├── .gitignore                   # Git 제외 파일
├── README.md                    # 프로젝트 문서
├── WINDOWS_SCHEDULER_GUIDE.md   # Windows 작업 스케줄러 가이드
│
├── firebase-key.json            # Firebase 인증 (Git 제외)
└── scheduler.log                # 스케줄러 로그 (Git 제외)
```

## 🔐 보안 주의사항

⚠️ **절대 Git에 커밋하지 말 것:**
- `firebase-key.json` (Firebase 인증 키)
- `.env` (환경 변수)
- `*.log` (로그 파일)
- MySQL 비밀번호

`.gitignore` 파일이 이미 설정되어 있습니다.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 TODO

- [ ] 추가 통화 지원 (EUR, JPY, CNY)
- [ ] 모바일 앱 개발
- [ ] 실시간 알림 기능
- [ ] 앙상블 모델 (Bi-LSTM + GRU + TCN)
- [ ] 예측 신뢰도 구간 표시

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 👤 작성자

**이재윤**
- 학번: 21011302
- 프로젝트: 파이썬기반 딥러닝 프로젝트 (기말 과제)
- 주제: 다변량 시계열 LSTM 모델을 이용한 여행자 대상 최적 환전 시점 예측 시스템 개발

## 🙏 감사의 말

- Yahoo Finance API for financial data
- FRED (Federal Reserve Economic Data) for economic indicators
- TensorFlow team for the amazing framework
- Firebase for cloud infrastructure

---

⭐ 이 프로젝트가 도움이 되었다면 Star를 눌러주세요!
