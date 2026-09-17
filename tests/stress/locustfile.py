"""
Locust stress test for the RAG Knowledge Base Q&A System.

Simulates real user workflow:
  1. Login (or register if new) -> get JWT token
  2. Create a chat session
  3. Send chat messages (SSE streaming) with think time
  4. Browse session history

Usage:
  locust -f tests/stress/locustfile.py --headless --host http://localhost:8000
         --users 100 --spawn-rate 5 --run-time 320s
         --html tests/stress/reports/report.html
"""
import json
import os
import sys
import time

from locust import HttpUser, task, between, events

# Add test config to path
sys.path.insert(0, os.path.dirname(__file__))
from config import SAMPLE_QUESTIONS


class RAGChatUser(HttpUser):
    """Simulates a single real user: login -> session -> chat -> browse."""

    wait_time = between(1, 5)  # Think time between actions: 1-5 seconds

    def on_start(self):
        """Called when a simulated user starts. Login (or register) and create session."""
        self.token = None
        self.user_id = None
        self.session_id = None
        self.question_index = 0
        self._login_or_register()
        self._create_session()

    # ---- Authentication ----

    def _login_or_register(self):
        """Login as a test user. Auto-register if user doesn't exist yet."""
        # Use a deterministic index from the environment runner
        idx = self._get_user_index()
        username = f"stresstest_{idx}"
        password = "TestPass123!"

        # Try login first
        with self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            catch_response=True,
            name="POST /api/auth/login",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.token = data["access_token"]
                self.user_id = data.get("user", {}).get("id")
                resp.success()
                return

        # Login failed -> register new user
        with self.client.post(
            "/api/auth/register",
            json={
                "username": username,
                "password": password,
                "email": f"{username}@test.local",
            },
            catch_response=True,
            name="POST /api/auth/register",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.token = data["access_token"]
                self.user_id = data.get("user", {}).get("id")
                resp.success()
            else:
                resp.failure(f"Register returned {resp.status_code}: {resp.text[:200]}")

    def _create_session(self):
        """Create a new chat session."""
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        with self.client.post(
            "/api/sessions",
            json={"title": "Stress Test Session"},
            headers=headers,
            catch_response=True,
            name="POST /api/sessions",
        ) as resp:
            if resp.status_code in (200, 201):
                data = resp.json()
                self.session_id = data["id"]
                resp.success()
            else:
                resp.failure(f"Session create returned {resp.status_code}: {resp.text[:200]}")

    # ---- Tasks (weighted) ----

    @task(70)
    def send_chat_message(self):
        """Main interaction: send message and receive SSE streaming response."""
        if not self.token or not self.session_id:
            self._login_or_register()
            self._create_session()
            if not self.session_id:
                return

        question = self._next_question()
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        start_time = time.time()

        with self.client.post(
            f"/api/chat/{self.session_id}",
            json={"message": question},
            headers=headers,
            catch_response=True,
            stream=True,
            name="POST /api/chat/{session_id} (SSE)",
        ) as response:
            if response.status_code != 200:
                response.failure(f"Chat returned {response.status_code}: {response.text[:200]}")
                # Re-create session on failure (may have been deleted or invalid)
                if response.status_code in (401, 404):
                    self._login_or_register()
                    self._create_session()
                return

            # Parse SSE stream
            token_count = 0
            citations_received = False
            done_received = False
            error_msg = None

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue

                etype = event.get("type")
                if etype == "token":
                    token_count += len(event.get("content", ""))
                elif etype == "citations":
                    citations_received = True
                elif etype == "done":
                    done_received = True
                elif etype == "error":
                    error_msg = event.get("content", "unknown error")
                    break

            elapsed_ms = int((time.time() - start_time) * 1000)

            if error_msg:
                response.failure(f"Chat SSE error: {error_msg}")
            elif done_received or token_count > 0:
                # "done" event OR received tokens = success
                response.success()
                # Custom metric: end-to-end chat latency
                events.request.fire(
                    request_type="SSE",
                    name="chat_e2e_latency",
                    response_time=elapsed_ms,
                    response_length=token_count,
                )
            else:
                response.failure("SSE stream completed without 'done' or tokens")

    @task(15)
    def list_sessions(self):
        """Browse session history."""
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        with self.client.get(
            "/api/sessions",
            headers=headers,
            catch_response=True,
            name="GET /api/sessions",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 401:
                self._login_or_register()
                resp.success()
            else:
                resp.failure(f"Sessions list returned {resp.status_code}")

    @task(10)
    def create_new_session(self):
        """Create a fresh chat session."""
        if not self.token:
            return
        self._create_session()

    @task(5)
    def health_check(self):
        """Lightweight health check to verify server is alive."""
        with self.client.get(
            "/api/health",
            catch_response=True,
            name="GET /api/health",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "ok":
                    resp.success()
                else:
                    resp.failure(f"Health check unexpected: {data}")
            else:
                resp.failure(f"Health check returned {resp.status_code}")

    # ---- Helpers ----

    _user_index_counter = 0

    def _get_user_index(self):
        """Get a unique index for this user across the test run."""
        # Use Locust's environment runner to get a unique ID
        if hasattr(self.environment, "runner") and self.environment.runner:
            RAGChatUser._user_index_counter += 1
            return RAGChatUser._user_index_counter % 120  # 0-119, wrap around
        return 0

    def _next_question(self):
        """Round-robin through sample questions for query diversity."""
        q = SAMPLE_QUESTIONS[self.question_index % len(SAMPLE_QUESTIONS)]
        self.question_index += 1
        return q
