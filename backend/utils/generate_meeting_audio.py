import os
import json
import random
import datetime
from pathlib import Path

# 회의 참가자 정보
PARTICIPANTS = [
    {"name": "김부장", "role": "팀장", "department": "마케팅팀"},
    {"name": "이대리", "role": "담당자", "department": "개발팀"},
    {"name": "박과장", "role": "기획자", "department": "기획팀"}
]

# 회의 주제 목록
MEETING_TOPICS = [
    "신규 프로젝트 기획 논의",
    "분기별 실적 검토",
    "마케팅 전략 수립",
    "신제품 출시 일정 조율",
    "고객 피드백 분석"
]

# 회의 내용 템플릿
MEETING_TEMPLATES = [
    [
        "{moderator}: 안녕하세요, {date} {topic} 회의를 시작하겠습니다. 오늘 참석해 주신 {p1_name}님, {p2_name}님 감사합니다.",
        "{p1_name}: 네, 안녕하세요. {p1_department}에서 온 {p1_name}입니다.",
        "{p2_name}: 반갑습니다. {p2_department} {p2_name}입니다.",
        "{moderator}: 오늘 회의에서는 {topic}에 대해 논의할 예정입니다. 먼저 {p1_name}님께서 현재 상황을 공유해 주시겠어요?",
        "{p1_name}: 네, 현재 저희 {p1_department}에서는 {custom_content_1}에 집중하고 있습니다. 특히 {custom_content_2} 부분에서 좋은 성과를 내고 있습니다.",
        "{moderator}: 좋은 소식이네요. {p2_name}님, 혹시 이와 관련해서 {p2_department} 쪽에서 의견이 있으신가요?",
        "{p2_name}: 네, 저희 {p2_department}에서는 {custom_content_3}에 대해 고민하고 있습니다. {p1_name}님이 말씀하신 {custom_content_2} 부분과 연계해서 {custom_content_4}를 제안드리고 싶습니다.",
        "{p1_name}: 좋은 제안이네요. 그렇다면 {custom_content_5}에 대해서도 함께 고려해보면 어떨까요?",
        "{p2_name}: 네, 그 부분도 중요하다고 생각합니다. 추가로 {custom_content_6}에 대한 계획도 세워야 할 것 같습니다.",
        "{moderator}: 두 분 모두 좋은 의견 감사합니다. 그럼 정리하자면, {custom_content_7}을 우선적으로 진행하고, 이후에 {custom_content_8}을 검토하는 방향으로 가면 될 것 같습니다.",
        "{p1_name}: 네, 동의합니다.",
        "{p2_name}: 저도 좋다고 생각합니다.",
        "{moderator}: 그럼 다음 회의는 2주 후에 진행하도록 하겠습니다. 오늘 회의는 여기서 마치겠습니다. 감사합니다."
    ]
]

# 커스텀 콘텐츠 목록
CUSTOM_CONTENTS = {
    "신규 프로젝트 기획 논의": [
        "사용자 경험 개선", 
        "모바일 앱 인터페이스", 
        "시장 조사 결과", 
        "프로토타입 개발 일정", 
        "사용자 테스트 계획", 
        "피드백 수집 방법", 
        "MVP 기능 정의", 
        "출시 전략"
    ],
    "분기별 실적 검토": [
        "매출 증가율", 
        "신규 고객 유치", 
        "비용 절감 방안", 
        "다음 분기 목표 설정", 
        "경쟁사 분석", 
        "마케팅 효과 측정", 
        "핵심 성과 지표 개선", 
        "리스크 관리 전략"
    ],
    "마케팅 전략 수립": [
        "소셜 미디어 캠페인", 
        "콘텐츠 마케팅 방향", 
        "타겟 고객층 분석", 
        "광고 예산 배분", 
        "브랜드 인지도 향상 방안", 
        "인플루언서 협업 전략", 
        "디지털 마케팅 채널 다각화", 
        "ROI 측정 방법론"
    ],
    "신제품 출시 일정 조율": [
        "생산 라인 준비 상태", 
        "품질 관리 프로세스", 
        "공급망 이슈", 
        "출시 이벤트 기획", 
        "사전 예약 시스템", 
        "초기 피드백 수집 계획", 
        "단계적 출시 전략", 
        "마케팅 자료 준비"
    ],
    "고객 피드백 분석": [
        "주요 불만 사항", 
        "개선 요청 사항", 
        "사용자 만족도 조사", 
        "피드백 우선순위화", 
        "개선 로드맵", 
        "고객 지원 시스템 강화", 
        "반복적인 이슈 해결 방안", 
        "긍정적 피드백 활용 전략"
    ]
}

def generate_meeting_script():
    """가상의 회의 스크립트를 생성합니다."""
    # 회의 날짜 생성 (현재 날짜 사용)
    today = datetime.datetime.now()
    date_str = today.strftime("%Y년 %m월 %d일")
    
    # 회의 주제 선택
    topic = random.choice(MEETING_TOPICS)
    
    # 참가자 역할 배정
    random.shuffle(PARTICIPANTS)
    moderator = PARTICIPANTS[0]["name"]
    p1 = PARTICIPANTS[1]
    p2 = PARTICIPANTS[2]
    
    # 템플릿 선택
    template = random.choice(MEETING_TEMPLATES)
    
    # 커스텀 콘텐츠 선택
    custom_contents = random.sample(CUSTOM_CONTENTS[topic], 8)
    
    # 스크립트 생성
    script = []
    for line in template:
        formatted_line = line.format(
            moderator=moderator,
            date=date_str,
            topic=topic,
            p1_name=p1["name"],
            p1_department=p1["department"],
            p1_role=p1["role"],
            p2_name=p2["name"],
            p2_department=p2["department"],
            p2_role=p2["role"],
            custom_content_1=custom_contents[0],
            custom_content_2=custom_contents[1],
            custom_content_3=custom_contents[2],
            custom_content_4=custom_contents[3],
            custom_content_5=custom_contents[4],
            custom_content_6=custom_contents[5],
            custom_content_7=custom_contents[6],
            custom_content_8=custom_contents[7]
        )
        script.append(formatted_line)
    
    return {"topic": topic, "date": date_str, "participants": PARTICIPANTS, "script": script}

def save_meeting_script(script_data, output_dir="meeting_scripts"):
    """생성된 회의 스크립트를 파일로 저장합니다."""
    # 출력 디렉토리 생성
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # 파일명 생성
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"meeting_{timestamp}.txt"
    json_filename = f"meeting_{timestamp}.json"
    
    # 텍스트 파일로 저장
    with open(output_path / filename, "w", encoding="utf-8") as f:
        f.write(f"회의 주제: {script_data['topic']}\n")
        f.write(f"날짜: {script_data['date']}\n")
        f.write("참가자:\n")
        for p in script_data['participants']:
            f.write(f"  - {p['name']} ({p['department']}, {p['role']})\n")
        f.write("\n회의 내용:\n")
        for line in script_data['script']:
            f.write(f"{line}\n")
    
    # JSON 파일로도 저장
    with open(output_path / json_filename, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)
    
    return output_path / filename, output_path / json_filename

def main():
    print("가상의 3자 대면 회의록 생성 중...")
    meeting_script = generate_meeting_script()
    txt_path, json_path = save_meeting_script(meeting_script)
    print(f"회의록이 생성되었습니다.")
    print(f"텍스트 파일: {txt_path}")
    print(f"JSON 파일: {json_path}")
    print("\n이 텍스트 파일을 TTS(Text-to-Speech) 서비스를 통해 음성 파일로 변환할 수 있습니다.")
    print("그 후, 생성된 음성 파일을 STT(Speech-to-Text) 서비스에 업로드하여 텍스트로 다시 변환할 수 있습니다.")

if __name__ == "__main__":
    main()