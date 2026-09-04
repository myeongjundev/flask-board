import os
from dotenv import load_dotenv

load_dotenv()  # 같은 폴더의 .env를 읽는다. 기존 셸 환경변수는 덮어쓰지 않는다.

key = os.environ.get("LLM_API_KEY")

# 키 전체를 출력하지 않는다.
if key:
    print("키 로드됨 - 앞 4자리:", key[:4] + "****")
else:
    print("키 없음 - 더미 실습 진행")
