import os
import sys
import logging
from tiro_service import TiroService

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_tiro_service():
    """
    Tiro 서비스 기능을 테스트합니다.
    환경 변수 TIRO_API_KEY가 설정되어 있어야 합니다.
    """
    # Tiro 서비스 인스턴스 생성
    tiro_service = TiroService()
    
    # 서비스 구성 확인
    if not tiro_service.is_configured():
        logger.error("Tiro 서비스가 구성되지 않았습니다. TIRO_API_KEY 환경 변수를 설정하세요.")
        return False
    
    logger.info(f"서비스 이름: {tiro_service.get_service_name()}")
    logger.info(f"지원되는 형식: {tiro_service.get_supported_formats()}")
    logger.info(f"최대 파일 크기: {tiro_service.get_max_file_size() / (1024 * 1024):.2f} MB")
    
    # 테스트 오디오 파일 경로 확인
    test_file = None
    test_dirs = ["./test_audio", "../test_audio", "./audio_samples", "../audio_samples"]
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            audio_files = [f for f in os.listdir(test_dir) 
                          if f.split('.')[-1].lower() in tiro_service.get_supported_formats()]
            if audio_files:
                test_file = os.path.join(test_dir, audio_files[0])
                break
    
    if not test_file:
        logger.error("테스트할 오디오 파일을 찾을 수 없습니다.")
        logger.info("다음 디렉토리에 오디오 파일을 추가하세요: ./test_audio 또는 ./audio_samples")
        return False
    
    logger.info(f"테스트 파일: {test_file}")
    
    # 파일 변환 테스트
    try:
        with open(test_file, "rb") as f:
            file_content = f.read()
        
        result = tiro_service.transcribe_file(
            file_content=file_content,
            filename=os.path.basename(test_file),
            language_code="ko"
        )
        
        if result.get("error"):
            logger.error(f"변환 오류: {result['error']}")
            return False
        
        logger.info("변환 결과:")
        logger.info(f"텍스트: {result.get('text', '')}")
        logger.info(f"신뢰도: {result.get('confidence', 0)}")
        logger.info(f"오디오 길이: {result.get('audio_duration', 0):.2f}초")
        logger.info(f"처리 시간: {result.get('processing_time', 0):.2f}초")
        
        return True
    
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {str(e)}")
        return False

if __name__ == "__main__":
    # 환경 변수 확인
    if not os.environ.get("TIRO_API_KEY"):
        print("TIRO_API_KEY 환경 변수를 설정하세요.")
        print("예: export TIRO_API_KEY=your_api_key (Linux/macOS)")
        print("예: set TIRO_API_KEY=your_api_key (Windows)")
        sys.exit(1)
    
    # 테스트 실행
    success = test_tiro_service()
    
    if success:
        print("\n✅ Tiro 서비스 테스트 성공!")
        sys.exit(0)
    else:
        print("\n❌ Tiro 서비스 테스트 실패!")
        sys.exit(1)