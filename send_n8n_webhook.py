"""이전 파일명을 위한 호환 실행기. 새 과제 파일은 alert_sender.py다."""
from alert_sender import main


if __name__ == "__main__":
    raise SystemExit(main())
