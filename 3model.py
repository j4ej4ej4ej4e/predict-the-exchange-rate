# ============================================================================
# 3model.py
# 구조: Bi-LSTM (2-Stack) + Huber Loss (이상치 강건성 확보)
# ============================================================================

import tensorflow as tf
from tensorflow.keras import layers, models, optimizers

def build_improved_model(input_shape):
    """
    R^2 음수 문제 해결을 위한 개선된 모델 구조
    - Bidirectional LSTM: 과거와 미래 방향 정보 모두 활용
    - Huber Loss: 금융 데이터의 튀는 값(Outlier)에 덜 민감하게 반응
    """
    model = models.Sequential()
    
    # 1. 입력층 & 1차 Bi-LSTM
    # return_sequences=True: 다음 LSTM 층으로 시퀀스를 그대로 전달
    model.add(layers.Input(shape=input_shape))
    model.add(layers.Bidirectional(layers.LSTM(64, return_sequences=True)))
    model.add(layers.BatchNormalization()) # 학습 안정화
    model.add(layers.Dropout(0.3)) # 과적합 방지
    
    # 2. 2차 Bi-LSTM
    # return_sequences=False: 마지막 시점의 벡터만 출력
    model.add(layers.Bidirectional(layers.LSTM(32, return_sequences=False)))
    model.add(layers.BatchNormalization())
    model.add(layers.Dropout(0.3))
    
    # 3. 출력층
    # 활성화 함수 Linear (수익률 예측 회귀 문제)
    model.add(layers.Dense(16, activation='relu'))
    model.add(layers.Dense(1, activation='linear')) 
    
    # 4. 컴파일
    # Huber Loss: MSE와 MAE의 장점을 결합 (이상치에 강함)
    optimizer = optimizers.Adam(learning_rate=0.001)
    model.compile(optimizer=optimizer, loss=tf.keras.losses.Huber(), metrics=['mae', 'mse'])
    
    return model

if __name__ == "__main__":
    model = build_improved_model((60, 25)) # 예시 shape
    model.summary()
    print("✅ 모델 빌드 테스트 완료")