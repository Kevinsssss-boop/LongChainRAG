"""消息评价接口。

这个接口原来同时有三个问题（写坏数据 / 越权 / 不校验会话归属），一次都没跑通，
所以这里的每条测试都对应一个具体的回归。
"""
import pytest

from app.models import ChatSession, Message

CITATIONS = [{"index": 1, "content": "片段内容", "source": "a.pdf", "score": 0.9}]


@pytest.fixture
def session_with_reply(db, admin_user):
    """一个属于 admin_user 的会话，内含一条带引用的助手回复和一条用户消息。"""
    session = ChatSession(user_id=admin_user.id, title="t")
    db.add(session)
    db.commit()
    db.refresh(session)

    reply = Message(
        session_id=session.id, role="assistant",
        content="这是回答", citations=list(CITATIONS),
    )
    question = Message(session_id=session.id, role="user", content="这是提问")
    db.add_all([reply, question])
    db.commit()
    db.refresh(reply)
    db.refresh(question)

    return session, reply, question


def _post(client, session_id, message_id, rating, headers):
    return client.post(
        f"/api/chat/{session_id}/feedback",
        json={"message_id": message_id, "rating": rating},
        headers=headers,
    )


class TestFeedbackRecordsRating:
    def test_records_rating(self, client, db, auth_headers, session_with_reply):
        session, reply, _ = session_with_reply

        resp = _post(client, session.id, reply.id, "up", auth_headers)

        assert resp.status_code == 200
        db.refresh(reply)
        assert reply.feedback == "up"

    def test_rating_can_be_changed(self, client, db, auth_headers, session_with_reply):
        session, reply, _ = session_with_reply

        _post(client, session.id, reply.id, "up", auth_headers)
        _post(client, session.id, reply.id, "down", auth_headers)

        db.refresh(reply)
        assert reply.feedback == "down"

    def test_rejects_unknown_rating(self, client, auth_headers, session_with_reply):
        """rating 用 Literal["up","down"] 校验。

        原来声明成 str，任意字符串都能写进库，前端拿到不认识的值只能静默忽略。
        """
        session, reply, _ = session_with_reply

        resp = _post(client, session.id, reply.id, "maybe", auth_headers)

        assert resp.status_code == 422


class TestFeedbackDoesNotCorruptCitations:
    """回归：评价绝不能动 citations 字段。

    原来写的是 `message.citations["feedback"] = rating`。citations 是 JSON
    **数组**，所以：
      * 带引用的消息 —— 对数组取字符串下标，直接 TypeError，每次调用都 500；
      * 没有引用的消息 —— 先把 citations 赋成 {}，等于把整个引用字段覆盖成
        一个 dict，那条消息从此在前端渲染不出来。
    现在评价存进独立的 messages.feedback 列。
    """

    def test_citations_preserved(self, client, db, auth_headers, session_with_reply):
        session, reply, _ = session_with_reply

        resp = _post(client, session.id, reply.id, "up", auth_headers)

        assert resp.status_code == 200, "带引用的消息原来必定 500"
        db.refresh(reply)
        assert reply.citations == CITATIONS, "citations 必须原样保留"
        assert reply.feedback == "up"

    def test_missing_citations_stay_none(self, client, db, auth_headers, admin_user):
        session = ChatSession(user_id=admin_user.id, title="t")
        db.add(session)
        db.commit()
        db.refresh(session)

        reply = Message(session_id=session.id, role="assistant",
                        content="没有引用的回答", citations=None)
        db.add(reply)
        db.commit()
        db.refresh(reply)

        resp = _post(client, session.id, reply.id, "down", auth_headers)

        assert resp.status_code == 200
        db.refresh(reply)
        assert reply.citations is None, "原来是把它覆盖成了 {'feedback': ...}"
        assert reply.feedback == "down"


class TestFeedbackAuthorization:
    def test_cannot_rate_someone_elses_message(
        self, client, session_with_reply, other_auth_headers
    ):
        """越权：原来只按 message_id 查，不校验消息属不属于当前用户。"""
        session, reply, _ = session_with_reply

        resp = _post(client, session.id, reply.id, "up", other_auth_headers)

        assert resp.status_code == 404

    def test_session_id_must_match(self, client, db, auth_headers, session_with_reply, admin_user):
        """URL 里的 session_id 和消息实际所属的会话必须一致。

        用一个属于自己、但不是这条消息所在会话的 session_id 去提交。
        """
        _, reply, _ = session_with_reply
        other_session = ChatSession(user_id=admin_user.id, title="另一个会话")
        db.add(other_session)
        db.commit()
        db.refresh(other_session)

        resp = _post(client, other_session.id, reply.id, "up", auth_headers)

        assert resp.status_code == 404

    def test_requires_authentication(self, client, session_with_reply):
        session, reply, _ = session_with_reply

        resp = client.post(
            f"/api/chat/{session.id}/feedback",
            json={"message_id": reply.id, "rating": "up"},
        )

        assert resp.status_code in (401, 403)

    def test_rejects_rating_a_user_message(self, client, auth_headers, session_with_reply):
        """只能给助手回复打分 —— 给用户自己的提问打分没有意义。"""
        session, _, question = session_with_reply

        resp = _post(client, session.id, question.id, "up", auth_headers)

        assert resp.status_code == 400
