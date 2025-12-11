# ============================================================================
# 3data_preprocess.py (성능 개선 버전)
# 목표: 절대 가격이 아닌 '변동률(Return)' 및 '기술적 지표' 위주로 데이터 재구성
# ============================================================================

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import warnings

warnings.filterwarnings('ignore')

# ============ 설정 ===========
MYSQL_CONFIG = {
    'user': 'root',
    'password': '0818',
    'host': 'localhost',
    'port': 3306,
    'db': 'exchangeDATAbase',
    'raw_table': 'macro_data',
    'processed_table': 'processed_macro_data_v3' # v3 테이블 사용
}

def get_engine():
    return create_engine(
        f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
        f"@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['db']}"
    )

def add_technical_indicators(df):
    """기술적 지표 추가 (RSI, MACD, Bollinger Bands)"""
    df = df.copy()
    
    # 이동평균
    df['ma7'] = df['usd_krw'].rolling(window=7).mean()
    df['ma60'] = df['usd_krw'].rolling(window=60).mean()
    
    # MACD
    exp12 = df['usd_krw'].ewm(span=12, adjust=False).mean()
    exp26 = df['usd_krw'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp12 - exp26
    
    # RSI
    delta = df['usd_krw'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    df['bb_mid'] = df['usd_krw'].rolling(window=20).mean()
    df['bb_std'] = df['usd_krw'].rolling(window=20).std()
    df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * 2)
    df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * 2)
    
    return df

def preprocess():
    engine = get_engine()
    
    # 1. 데이터 로드
    print("🔄 데이터 로드 중...")
    query = f"SELECT * FROM {MYSQL_CONFIG['raw_table']} ORDER BY date ASC"
    df = pd.read_sql(query, engine)
    
    # 2. 결측치 보간 (선형)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].interpolate(method='linear')
    df = df.dropna() # 앞부분 보간 안된 데이터 제거
    
    # 3. 기술적 지표 추가
    print("🛠 기술적 지표 생성 중...")
    df = add_technical_indicators(df)
    
    # 4. [핵심] Target 생성: 7일 뒤 수익률 (Log Return)
    # y = ln(Price_t+7 / Price_t)
    # 값이 0보다 크면 상승, 작으면 하락
    FORECAST_DAYS = 7
    df['target_return'] = np.log(df['usd_krw'].shift(-FORECAST_DAYS) / df['usd_krw'])
    
    # 5. [핵심] Feature Engineering: 가격 자체보다는 변화율 사용
    # 모델이 1400원이라는 숫자보다 "어제보다 0.5% 올랐다"는 정보를 더 잘 학습함
    for col in ['wti_price', 'sp500_index', 'kospi_index', 'gold', 'dxy']:
        df[f'{col}_chg'] = df[col].pct_change()
        
    # 6. NaN 제거 (Shift 및 지표 계산으로 생긴 결측)
    df = df.dropna()
    
    # 7. 저장
    print(f"💾 {MYSQL_CONFIG['processed_table']}에 저장 중... (데이터 수: {len(df)})")
    df.to_sql(name=MYSQL_CONFIG['processed_table'], con=engine, if_exists='replace', index=False)
    print("✅ 전처리 완료!")

if __name__ == "__main__":
    preprocess()