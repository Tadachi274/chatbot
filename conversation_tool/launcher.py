from pathlib import Path
import sys


if __package__ in (None, "", "conversation_tool"):
    chatbot_dir = Path(__file__).resolve().parents[1]
    parent_dir = chatbot_dir.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    __package__ = "chatbot.conversation_tool"

from .main import main


if __name__ == "__main__":
    main()
