# ============================================================================
# data_get.py (수정 버전)
# 원본 데이터 자동 수집 및 MySQL 적재 (증분 업데이트)
# ============================================================================

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fredapi import Fred
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import warnings

warnings.filterwarnings('ignore')

# ============ 설정 ============
FRED_API_KEY = ""

# MySQL 접속 정보
MYSQL_CONFIG = {
    'user': '',
    'password': '',
    'host': '',
    'port': ,
    'db': ''
}

# 데이터 수집 기간
INITIAL_YEARS = 15  # 최초 실행 시 15년치


# ============ MySQL 연결 함수 ============
def create_database_if_not_exists():
    """데이터베이스 생성"""
    try:
        engine_no_db = create_engine(
            f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
            f"@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}"
        )
        
        with engine_no_db.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {MYSQL_CONFIG['db']} DEFAULT CHARACTER SET utf8mb4"))
            conn.commit()
        
        print(f"✅ 데이터베이스 '{MYSQL_CONFIG['db']}' 확인/생성 완료")
        engine_no_db.dispose()
        return True
        
    except SQLAlchemyError as e:
        print(f"❌ 데이터베이스 생성 실패: {e}")
        return False


def get_engine():
    """SQLAlchemy Engine 생성"""
    try:
        engine = create_engine(
            f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
            f"@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['db']}",
            pool_pre_ping=True,
            pool_recycle=3600
        )
        return engine
        
    except SQLAlchemyError as e:
        print(f"❌ 엔진 생성 실패: {e}")
        return None


def create_table_if_not_exists(engine):
    """테이블 생성 (15개 Feature)"""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS macro_data (
        date DATE PRIMARY KEY,
        usd_krw FLOAT NOT NULL COMMENT '원/달러 환율 (Target)',
        wti_price FLOAT COMMENT 'WTI 유가',
        sp500_index FLOAT COMMENT 'S&P 500 지수',
        kospi_index FLOAT COMMENT 'KOSPI 지수',
        kospi_volatility FLOAT COMMENT 'KOSPI 일별 변동률',
        usd_jpy FLOAT COMMENT '달러/엔 환율',
        usd_cny FLOAT COMMENT '달러/위안 환율',
        eur_usd FLOAT COMMENT '유로/달러 환율',
        vix FLOAT COMMENT '변동성 지수 (VIX)',
        gold FLOAT COMMENT '금 가격',
        dxy FLOAT COMMENT '달러 인덱스',
        us_rate FLOAT COMMENT '미국 기준금리',
        kr_rate FLOAT COMMENT '한국 기준금리',
        ird FLOAT COMMENT '금리차 (IRD)',
        ust_spread FLOAT COMMENT '미국 장단기 금리차 (10Y-2Y)',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_date (date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='환율 예측용 거시경제 데이터'
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(create_table_query))
            conn.commit()
        print("✅ 테이블 'macro_data' 확인/생성 완료")
        return True
        
    except SQLAlchemyError as e:
        print(f"❌ 테이블 생성 실패: {e}")
        return False


def get_last_date_in_db(engine):
    """DB에 저장된 가장 최근 날짜 조회"""
    try:
        query = "SELECT MAX(date) as last_date FROM macro_data"
        df = pd.read_sql(query, engine)
        
        if df['last_date'].iloc[0] is not None:
            last_date = pd.to_datetime(df['last_date'].iloc[0])
            print(f"   📅 DB 마지막 날짜: {last_date.date()}")
            return last_date
        
        print("   ℹ️  DB가 비어있음 (최초 실행)")
        return None
        
    except SQLAlchemyError as e:
        print(f"❌ 날짜 조회 실패: {e}")
        return None


# ============ 데이터 수집 함수 ============
def get_market_data(start_date, end_date):
    """Yahoo Finance 데이터 수집"""
    print(f"\n📊 [시장 데이터 수집] {start_date} ~ {end_date}")
    
    tickers = {
        'USD/KRW': 'KRW=X',
        'WTI_Price': 'CL=F',
        'SP500_Index': '^GSPC',
        'KOSPI_Index': '^KS11',
        'USD/JPY': 'JPY=X',
        'USD/CNY': 'CNY=X',
        'EUR/USD': 'EURUSD=X',
        'VIX': '^VIX',
        'Gold': 'GC=F',
        'DXY': 'DX-Y.NYB'
    }
    
    data_frames = {}
    success_count = 0
    
    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, start=start_date, end=end_date, 
                            progress=False, auto_adjust=False)
            
            if df.empty:
                print(f"   ⚠️  {name}: 데이터 없음")
                continue
            
            close_data = df['Close'].iloc[:, 0] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            close_data.name = name
            data_frames[name] = close_data
            success_count += 1
            print(f"   ✓ {name}: {len(close_data)}개")
            
        except Exception as e:
            print(f"   ✗ {name} 실패: {e}")
    
    print(f"\n   📊 수집 완료: {success_count}/{len(tickers)} Feature")
    
    if data_frames:
        combined_df = pd.concat(data_frames.values(), axis=1).dropna(how='all')
        combined_df = combined_df.interpolate(method='linear').ffill().bfill()
        
        # KOSPI Volatility 생성
        if 'KOSPI_Index' in combined_df.columns:
            combined_df['KOSPI_Volatility'] = combined_df['KOSPI_Index'].pct_change().abs() * 100
            combined_df['KOSPI_Volatility'] = combined_df['KOSPI_Volatility'].replace([np.inf, -np.inf], np.nan).fillna(0)
            print(f"   ✓ KOSPI_Volatility Feature 생성 완료")
        
        return combined_df
    
    return pd.DataFrame()


def get_interest_rate_data(start_date, end_date):
    """FRED 금리 데이터 수집"""
    print(f"\n📈 [금리 데이터 수집] {start_date} ~ {end_date}")
    
    try:
        fred = Fred(api_key=FRED_API_KEY)
        us_rate = fred.get_series('FEDFUNDS', start_date, end_date).rename('US_Rate')
        kr_rate = fred.get_series('IRLTLT01KRM156N', start_date, end_date).rename('KR_Rate')
        ust_spread = fred.get_series('T10Y2Y', start_date, end_date).rename('UST_Spread')
        
        rate_df = pd.concat([us_rate, kr_rate, ust_spread], axis=1).dropna(how='all')
        
        # 일별로 확장 (forward fill)
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        rate_df = rate_df.reindex(date_range).ffill().bfill()
        
        print(f"   ✓ US_Rate: {len(us_rate.dropna())}개")
        print(f"   ✓ KR_Rate: {len(kr_rate.dropna())}개")
        print(f"   ✓ UST_Spread: {len(ust_spread.dropna())}개")
        
        return rate_df
        
    except Exception as e:
        print(f"   ✗ FRED 실패: {e}")
        return pd.DataFrame()


def collect_and_integrate_data(start_date, end_date):
    """데이터 수집 + 통합"""
    market_df = get_market_data(start_date, end_date)
    rate_df = get_interest_rate_data(start_date, end_date)
    
    if market_df.empty or rate_df.empty:
        print("❌ 데이터 수집 실패")
        return None
    
    # 병합
    final_df = market_df.join(rate_df, how='inner')
    
    # IRD 계산
    final_df['IRD'] = final_df['US_Rate'] - final_df['KR_Rate']
    
    # 결측치 처리
    final_df = final_df.interpolate(method='linear').ffill().bfill().dropna()
    
    print(f"\n✅ 통합 완료: {len(final_df)}일치 데이터")
    print(f"   Feature 수: {len(final_df.columns)}개")
    
    return final_df


# ============ MySQL 저장 ============
def insert_data_to_db(engine, df):
    """신규 데이터 DB 삽입 (UPSERT)"""
    if df.empty:
        print("⚠️  삽입할 데이터 없음")
        return 0
    
    try:
        temp_table = 'temp_macro_data'
        
        # 컬럼명 매핑
        df_to_insert = df.copy()
        column_mapping = {
            'USD/KRW': 'usd_krw',
            'WTI_Price': 'wti_price',
            'SP500_Index': 'sp500_index',
            'KOSPI_Index': 'kospi_index',
            'KOSPI_Volatility': 'kospi_volatility',
            'USD/JPY': 'usd_jpy',
            'USD/CNY': 'usd_cny',
            'EUR/USD': 'eur_usd',
            'VIX': 'vix',
            'Gold': 'gold',
            'DXY': 'dxy',
            'US_Rate': 'us_rate',
            'KR_Rate': 'kr_rate',
            'IRD': 'ird',
            'UST_Spread': 'ust_spread'
        }
        df_to_insert = df_to_insert.rename(columns=column_mapping)
        df_to_insert.index.name = 'date'
        df_to_insert = df_to_insert.reset_index()
        
        # 임시 테이블에 데이터 삽입
        df_to_insert.to_sql(temp_table, engine, if_exists='replace', index=False)
        
        # UPSERT 쿼리
        upsert_query = f"""
        INSERT INTO macro_data 
            (date, usd_krw, wti_price, sp500_index, kospi_index, kospi_volatility, 
             usd_jpy, usd_cny, eur_usd, vix, gold, dxy, us_rate, kr_rate, ird, ust_spread)
        SELECT 
            date, usd_krw, wti_price, sp500_index, kospi_index, kospi_volatility,
            usd_jpy, usd_cny, eur_usd, vix, gold, dxy, us_rate, kr_rate, ird, ust_spread
        FROM {temp_table}
        ON DUPLICATE KEY UPDATE
            usd_krw = VALUES(usd_krw),
            wti_price = VALUES(wti_price),
            sp500_index = VALUES(sp500_index),
            kospi_index = VALUES(kospi_index),
            kospi_volatility = VALUES(kospi_volatility),
            usd_jpy = VALUES(usd_jpy),
            usd_cny = VALUES(usd_cny),
            eur_usd = VALUES(eur_usd),
            vix = VALUES(vix),
            gold = VALUES(gold),
            dxy = VALUES(dxy),
            us_rate = VALUES(us_rate),
            kr_rate = VALUES(kr_rate),
            ird = VALUES(ird),
            ust_spread = VALUES(ust_spread)
        """
        
        with engine.connect() as conn:
            conn.execute(text(upsert_query))
            conn.commit()
            conn.execute(text(f"DROP TABLE IF EXISTS {temp_table}"))
            conn.commit()
        
        insert_count = len(df_to_insert)
        print(f"✅ {insert_count}개 데이터 삽입/갱신 완료")
        return insert_count
        
    except SQLAlchemyError as e:
        print(f"❌ 데이터 삽입 실패: {e}")
        return 0


# ============ 메인 로직 ============
def auto_update_database():
    """DB 자동 업데이트 (증분)"""
    print("\n" + "="*80)
    print("🔄 MySQL 자동 업데이트 시작")
    print("="*80)
    
    # 1. 데이터베이스 생성
    if not create_database_if_not_exists():
        return False
    
    # 2. Engine 생성
    engine = get_engine()
    if not engine:
        return False
    
    # 3. 테이블 생성
    if not create_table_if_not_exists(engine):
        engine.dispose()
        return False
    
    # 4. 마지막 날짜 확인
    last_date = get_last_date_in_db(engine)
    
    # 5. 수집 기간 결정
    end_date = datetime.now()
    
    if last_date is None:
        # 최초 실행: 15년치
        start_date = end_date - timedelta(days=INITIAL_YEARS * 365)
        print(f"\n📥 최초 데이터 수집 ({INITIAL_YEARS}년치)")
    else:
        # 증분 업데이트: 마지막 날짜 다음날부터
        start_date = last_date + timedelta(days=1)
        
        # 이미 최신인지 확인
        if start_date.date() >= end_date.date():
            print(f"\n✅ 이미 최신 상태입니다! (마지막: {last_date.date()})")
            engine.dispose()
            return True
        
        print(f"\n📥 증분 업데이트")
    
    print(f"   수집 기간: {start_date.date()} ~ {end_date.date()}")
    
    # 6. 데이터 수집
    new_data = collect_and_integrate_data(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )
    
    if new_data is None or new_data.empty:
        print("\n⚠️  신규 데이터 없음")
        engine.dispose()
        return True
    
    # 7. DB 삽입
    insert_count = insert_data_to_db(engine, new_data)
    
    # 8. 최종 상태 확인
    final_query = """
    SELECT 
        COUNT(*) as total,
        MIN(date) as first_date,
        MAX(date) as last_date
    FROM macro_data
    """
    result = pd.read_sql(final_query, engine)
    
    engine.dispose()
    
    print(f"\n{'='*80}")
    print(f"✅ 업데이트 완료!")
    print(f"{'='*80}")
    print(f"   - 추가/갱신: {insert_count}개")
    print(f"   - 전체 데이터: {result['total'].iloc[0]}개")
    print(f"   - 기간: {result['first_date'].iloc[0]} ~ {result['last_date'].iloc[0]}")
    print(f"{'='*80}\n")
    
    return True


# ============ 데이터 조회 (수정 버전) ============
def load_data_from_db(start_date=None, end_date=None, limit=None, recent=True):
    """
    DB에서 데이터 로드
    
    Args:
        recent: True이면 최신 데이터부터, False면 오래된 데이터부터
    """
    engine = get_engine()
    if not engine:
        return None
    
    query = """
    SELECT date, usd_krw, wti_price, sp500_index, kospi_index, kospi_volatility, 
           usd_jpy, usd_cny, eur_usd, vix, gold, dxy, us_rate, kr_rate, ird, ust_spread 
    FROM macro_data
    """
    
    conditions = []
    if start_date:
        conditions.append(f"date >= '{start_date}'")
    if end_date:
        conditions.append(f"date <= '{end_date}'")
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    # 정렬 순서 (recent=True이면 최신순)
    query += " ORDER BY date DESC" if recent else " ORDER BY date ASC"
    
    if limit:
        query += f" LIMIT {limit}"
    
    try:
        df = pd.read_sql(query, engine, index_col='date', parse_dates=['date'])
        
        # 컬럼명 변경
        df.columns = ['USD/KRW', 'WTI_Price', 'SP500_Index', 'KOSPI_Index', 'KOSPI_Volatility', 
                      'USD/JPY', 'USD/CNY', 'EUR/USD', 'VIX', 'Gold', 'DXY', 
                      'US_Rate', 'KR_Rate', 'IRD', 'UST_Spread']
        
        print(f"✅ DB 로드 완료: {len(df)}개")
        if len(df) > 0:
            print(f"   기간: {df.index.min().date()} ~ {df.index.max().date()}")
        
        engine.dispose()
        return df
        
    except SQLAlchemyError as e:
        print(f"❌ 로드 실패: {e}")
        engine.dispose()
        return None


def show_db_summary():
    """DB 요약 정보"""
    engine = get_engine()
    if not engine:
        return
    
    try:
        query = """
        SELECT 
            COUNT(*) as total_rows,
            MIN(date) as first_date,
            MAX(date) as last_date,
            AVG(usd_krw) as avg_usd_krw,
            MIN(usd_krw) as min_usd_krw,
            MAX(usd_krw) as max_usd_krw
        FROM macro_data
        """
        
        df = pd.read_sql(query, engine)
        
        if df['total_rows'].iloc[0] > 0:
            print("\n" + "="*80)
            print("📊 DB 요약 정보")
            print("="*80)
            print(f"총 데이터: {int(df['total_rows'].iloc[0])}개")
            print(f"기간: {df['first_date'].iloc[0]} ~ {df['last_date'].iloc[0]}")
            
            days = int(df['total_rows'].iloc[0])
            years = days / 365
            print(f"수집 기간: 약 {years:.1f}년")
            
            print(f"\n[Target 통계 - USD/KRW]")
            print(f"  평균: {df['avg_usd_krw'].iloc[0]:.2f}원")
            print(f"  범위: {df['min_usd_krw'].iloc[0]:.2f} ~ {df['max_usd_krw'].iloc[0]:.2f}원")
            
            TIME_STEPS = 30
            FORECAST_DAYS = 7
            available_samples = days - TIME_STEPS - FORECAST_DAYS + 1
            train_samples = int(available_samples * 0.8)
            test_samples = available_samples - train_samples
            
            print(f"\n[학습 정보 (T=30, N=7)]")
            print(f"  학습 가능 샘플: {available_samples}개")
            print(f"  Train/Test: {train_samples} / {test_samples}개")
            
            print("="*80 + "\n")
        else:
            print("\n📊 DB가 비어있습니다.\n")
        
        engine.dispose()
        
    except SQLAlchemyError as e:
        print(f"❌ 요약 정보 조회 실패: {e}")


# ============ 실행 ============
if __name__ == "__main__":
    print("\n🚀 환율 예측 시스템 - 원본 데이터 수집기")
    print("="*80)
    
    # 1. 자동 업데이트
    success = auto_update_database()
    
    if success:
        # 2. DB 요약
        show_db_summary()
        
        # 3. 최근 5일 데이터 확인
        print("📋 최근 5일 데이터:")
        print("-"*80)
        recent_data = load_data_from_db(limit=5, recent=True)  # recent=True 추가!
        if recent_data is not None and len(recent_data) > 0:
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            print(recent_data)
            print("-"*80)
    else:

        print("\n❌ 업데이트 실패")
