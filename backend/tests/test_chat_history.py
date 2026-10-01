"""会话历史：必须取**最近**的 N 条，而不是最旧的 N 条。"""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.models import ChatSession, Message
from app.services.chat_service import ChatService


def _make_session(db, user_id, count=15):
    """造 count 轮问答。

    编号用两位数（问题01 而不是 问题1）—— 否则「问题1」是「问题11」的子串，
    `not in history` 这种断言会误判。
    """
    session = ChatSession(user_id=user_id, title="t")
    db.add(session)
    db.commit()
    db.refresh(session)

    base = datetime(2026, 1, 1, 12, 0, 0)
    for i in range(1, count + 1):
        db.add(Message(
            session_id=session.id, role="user", content=f"问题{i:02d}",
            created_at=base + timedelta(minutes=2 * i),
        ))
        db.add(Message(
            session_id=session.id, role="assistant", content=f"回答{i:02d}",
            created_at=base + timedelta(minutes=2 * i + 1),
        ))
    db.commit()
    return session


@pytest.fixture
def service(db):
    # ChatService.__init__ 会建 Chroma 客户端和 embedder，这个单元测试用不到
    with patch('app.services.chat_service.HybridRetriever'), \
         patch('app.services.chat_service.Reranker'), \
         patch('app.services.chat_service.get_semantic_cache'):
        yield ChatService(db)


class TestChatHistory:
    def test_returns_most_recent_not_oldest(self, service, db, admin_user):
        """对话超过 10 条后，模型看到的必须是最近的 10 条。

        原实现是 .order_by(Message.created_at).limit(10) —— 升序取前 10 条，
        也就是这个会话**最旧**的 10 条。一旦对话超过 10 条，上下文就永久冻结
        在开头，之后说的每句话模型都看不见，「多轮对话」从第 11 条消息起失效。
        """
        session = _make_session(db, admin_user.id, count=15)

        history = service._get_chat_history(session.id)

        assert "问题15" in history, "最近一轮必须出现在历史里"
        assert "回答15" in history
        assert "问题01" not in history, "最旧的一轮不该出现 —— 出现说明取的是最旧的 10 条"

    def test_returns_at_most_limit_messages(self, service, db, admin_user):
        session = _make_session(db, admin_user.id, count=15)

        history = service._get_chat_history(session.id, limit=4)

        # 最后 4 条 = 问题14 / 回答14 / 问题15 / 回答15
        assert "问题15" in history
        assert "回答15" in history
        assert "问题14" in history
        assert "问题13" not in history

    def test_chronological_order(self, service, db, admin_user):
        """拼出来的文本要按时间正序（先问后答）。

        实现是先 desc + limit 取最近的，再翻回正序。漏掉那一步翻转的话，
        顺序会整个倒过来，模型会看到「回答在前、问题在后」。
        """
        session = _make_session(db, admin_user.id, count=3)

        history = service._get_chat_history(session.id)

        assert history.index("问题03") < history.index("回答03")

    def test_excludes_current_question(self, service, db, admin_user):
        """本轮正在问的消息要排掉。

        调用方在进入生成流程时就已经把用户消息写库了，不排掉的话它会在提示词
        里出现两次 —— 历史里一次，末尾的「用户问题：{question}」又一次。
        """
        session = _make_session(db, admin_user.id, count=3)
        current = Message(
            session_id=session.id, role="user", content="本轮的问题99",
            created_at=datetime(2026, 1, 1, 13, 0, 0),
        )
        db.add(current)
        db.commit()
        db.refresh(current)

        history = service._get_chat_history(session.id, exclude_message_id=current.id)

        assert "本轮的问题99" not in history

    def test_empty_session_says_so(self, service, db, admin_user):
        session = ChatSession(user_id=admin_user.id, title="t")
        db.add(session)
        db.commit()

        assert service._get_chat_history(session.id) == "（无历史对话）"
