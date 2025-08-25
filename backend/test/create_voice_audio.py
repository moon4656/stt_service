import numpy as np
import wave
import struct
import math

def create_voice_like_audio(filename="voice_test.wav", duration=5, sample_rate=16000):
    """
    음성과 유사한 오디오 파일 생성
    여러 주파수를 조합하여 음성과 비슷한 패턴 생성
    """
    
    # 시간 배열 생성
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # 기본 주파수들 (인간 음성 범위)
    fundamental_freq = 150  # 기본 주파수 (Hz)
    
    # 복합 음성 신호 생성
    signal = np.zeros_like(t)
    
    # 기본 주파수와 하모닉 추가
    for harmonic in [1, 2, 3, 4, 5]:
        freq = fundamental_freq * harmonic
        amplitude = 1.0 / harmonic  # 하모닉일수록 작은 진폭
        signal += amplitude * np.sin(2 * np.pi * freq * t)
    
    # 포먼트 주파수 추가 (모음 'a' 소리와 유사)
    formant1 = 730  # 첫 번째 포먼트
    formant2 = 1090  # 두 번째 포먼트
    
    signal += 0.3 * np.sin(2 * np.pi * formant1 * t)
    signal += 0.2 * np.sin(2 * np.pi * formant2 * t)
    
    # 진폭 변조 (음성의 자연스러운 변화)
    modulation = 1 + 0.3 * np.sin(2 * np.pi * 3 * t)  # 3Hz 변조
    signal *= modulation
    
    # 노이즈 추가 (자연스러운 음성을 위해)
    noise = 0.05 * np.random.normal(0, 1, len(signal))
    signal += noise
    
    # 정규화
    signal = signal / np.max(np.abs(signal))
    
    # 16비트 정수로 변환
    signal_int = (signal * 32767).astype(np.int16)
    
    # WAV 파일로 저장
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # 모노
        wav_file.setsampwidth(2)  # 16비트
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(signal_int.tobytes())
    
    print(f"✅ 음성 유사 오디오 파일 생성 완료: {filename}")
    print(f"   - 길이: {duration}초")
    print(f"   - 샘플레이트: {sample_rate}Hz")
    print(f"   - 기본 주파수: {fundamental_freq}Hz")
    print(f"   - 포먼트: {formant1}Hz, {formant2}Hz")
    
    return filename

def create_speech_pattern_audio(filename="speech_pattern.wav", duration=8, sample_rate=16000):
    """
    음성 패턴을 모방한 오디오 생성
    단어와 휴지기를 포함한 패턴
    """
    
    total_samples = int(sample_rate * duration)
    signal = np.zeros(total_samples)
    
    # 단어 패턴 생성 (0.5초 음성, 0.2초 휴지기)
    word_duration = 0.5  # 단어 길이
    pause_duration = 0.2  # 휴지기 길이
    pattern_duration = word_duration + pause_duration
    
    current_time = 0
    
    while current_time + word_duration < duration:
        start_sample = int(current_time * sample_rate)
        end_sample = int((current_time + word_duration) * sample_rate)
        
        # 단어 부분 생성
        word_samples = end_sample - start_sample
        t_word = np.linspace(0, word_duration, word_samples, False)
        
        # 음성 주파수 (100-300Hz 범위에서 변화)
        base_freq = 150 + 50 * np.sin(2 * np.pi * current_time / 2)
        
        # 복합 음성 신호
        word_signal = np.zeros_like(t_word)
        for harmonic in [1, 2, 3]:
            freq = base_freq * harmonic
            amplitude = 1.0 / harmonic
            word_signal += amplitude * np.sin(2 * np.pi * freq * t_word)
        
        # 엔벨로프 적용 (자연스러운 시작과 끝)
        envelope = np.sin(np.pi * t_word / word_duration)
        word_signal *= envelope
        
        # 신호에 추가
        signal[start_sample:end_sample] = word_signal
        
        current_time += pattern_duration
    
    # 정규화
    if np.max(np.abs(signal)) > 0:
        signal = signal / np.max(np.abs(signal))
    
    # 16비트 정수로 변환
    signal_int = (signal * 32767).astype(np.int16)
    
    # WAV 파일로 저장
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(signal_int.tobytes())
    
    print(f"✅ 음성 패턴 오디오 파일 생성 완료: {filename}")
    print(f"   - 길이: {duration}초")
    print(f"   - 샘플레이트: {sample_rate}Hz")
    print(f"   - 패턴: {word_duration}초 음성 + {pause_duration}초 휴지기")
    
    return filename

if __name__ == "__main__":
    print("🎤 음성 유사 오디오 파일 생성 중...")
    
    # 두 가지 타입의 오디오 생성
    create_voice_like_audio("voice_like_test.wav", duration=6)
    create_speech_pattern_audio("speech_pattern_test.wav", duration=8)
    
    print("\n✅ 모든 오디오 파일 생성 완료!")