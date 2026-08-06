"""Tests for Pydantic schemas — Input validation."""
import pytest
import sys
sys.path.insert(0, '.')

from app.schemas import (
    UserRegister, UserLogin, TokenResponse,
    SessionCreate, PaginationParams, ChatRequest,
)


class TestUserRegister:
    """Test user registration schema validation."""

    def test_valid_registration(self):
        data = UserRegister(username="testuser", password="pass123456")
        assert data.username == "testuser"
        assert data.password == "pass123456"

    def test_username_too_short(self):
        with pytest.raises(Exception):  # ValidationError
            UserRegister(username="a", password="123456")

    def test_password_too_short(self):
        with pytest.raises(Exception):
            UserRegister(username="valid_user", password="123")

    def test_optional_email(self):
        data = UserRegister(username="valid_user", password="123456", email="test@example.com")
        assert data.email == "test@example.com"


class TestUserLogin:
    """Test login schema validation."""

    def test_valid_login(self):
        data = UserLogin(username="admin", password="123456")
        assert data.username == "admin"
        assert data.password == "123456"


class TestSessionCreate:
    """Test session creation schema."""

    def test_default_title(self):
        data = SessionCreate()
        assert data.title == "新对话"

    def test_custom_title(self):
        data = SessionCreate(title="My Chat")
        assert data.title == "My Chat"


class TestPaginationParams:
    """Test pagination parameter validation."""

    def test_defaults(self):
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 20

    def test_page_zero_rejected(self):
        with pytest.raises(Exception):
            PaginationParams(page=0)

    def test_page_size_too_large(self):
        with pytest.raises(Exception):
            PaginationParams(page_size=200)


class TestChatRequest:
    """Test chat request validation."""

    def test_valid_message(self):
        req = ChatRequest(message="Hello AI")
        assert req.message == "Hello AI"

    def test_empty_message_rejected(self):
        with pytest.raises(Exception):
            ChatRequest(message="")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
