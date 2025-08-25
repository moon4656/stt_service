import wave
import math
import struct

def create_test_audio(filename, duration_seconds=5, sample_rate=16000):
    """
    실제 오디오 데이터가 포함된 WAV 파일 생성
    """
    # 사인파 생성 (440Hz - A4 음)
    frequency = 440.0
    frames = int(duration_seconds * sample_rate)
    
    # 사인파 데이터 생성
    audio_data = []
    for i in range(frames):
        # 사인파 계산
        value = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * i / sample_rate))
        # 16비트 정수로 변환
        audio_data.append(struct.pack('<h', value))
    
    # WAV 파일 생성
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)  # 모노
        wav_file.setsampwidth(2)  # 16비트
        wav_file.setframerate(sample_rate)  # 샘플레이트
        wav_file.writeframes(b''.join(audio_data))
    
    print(f"✅ 테스트 오디오 파일 생성 완료: {filename}")
    print(f"   - 길이: {duration_seconds}초")
    print(f"   - 샘플레이트: {sample_rate}Hz")
    print(f"   - 주파수: {frequency}Hz")

if __name__ == "__main__":
    create_test_audio("real_test_audio.wav", duration_seconds=10)