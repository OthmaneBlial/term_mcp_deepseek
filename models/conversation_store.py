"""
Conversation Store and Session Management
Manages conversations and sessions for different users
"""

import threading
import time
import secrets
from typing import Dict, List, Any, Optional
from config import config

class Session:
    """Represents a user session"""

    def __init__(self, user_id: str, client_id: str = None):
        self.session_id = secrets.token_urlsafe(32)
        self.user_id = user_id
        self.client_id = client_id or user_id
        self.created_at = time.time()
        self.last_activity = time.time()
        self.is_active = True

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()

    def is_expired(self) -> bool:
        """Check if session has expired"""
        return (time.time() - self.last_activity) > config.SESSION_TIMEOUT

    def get_age(self) -> float:
        """Get session age in seconds"""
        return time.time() - self.created_at

class ConversationStore:
    """Thread-safe conversation and session storage"""

    def __init__(self):
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()
        self._default_conversation = self._create_default_conversation()

    def _create_default_conversation(self) -> List[Dict[str, Any]]:
        """Create the default system conversation"""
        return [
            {
                "role": "system",
                "content": (
                    "You are a helpful AI assistant with terminal access. "
                    "If you need to run a shell command to answer the user, include a line in your assistant message:\n"
                    "CMD: the_command_here\n\n"
                    "The server will intercept that line, run the command, and append the actual output to your final message. "
                    "Only use 'CMD:' if you truly need to run a command."
                )
            }
        ]

    def get_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation for a session, creating if it doesn't exist"""
        with self._lock:
            if session_id not in self._conversations:
                self._conversations[session_id] = self._default_conversation.copy()
            return self._conversations[session_id]

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to a conversation"""
        with self._lock:
            conversation = self.get_conversation(session_id)
            conversation.append({
                "role": role,
                "content": content
            })

            # Limit conversation length to prevent memory issues
            if len(conversation) > 100:  # Keep last 100 messages
                # Keep system message and last 99 messages
                system_msg = conversation[0] if conversation[0]["role"] == "system" else None
                if system_msg:
                    conversation[:] = [system_msg] + conversation[-99:]
                else:
                    conversation[:] = conversation[-99:]

    def clear_conversation(self, session_id: str):
        """Clear conversation for a session"""
        with self._lock:
            if session_id in self._conversations:
                self._conversations[session_id] = self._default_conversation.copy()

    def get_all_sessions(self) -> List[str]:
        """Get all active session IDs"""
        with self._lock:
            return list(self._conversations.keys())

    def create_session(self, user_id: str, client_id: str = None) -> Session:
        """Create a new session for a user"""
        with self._lock:
            session = Session(user_id, client_id)
            self._sessions[session.session_id] = session
            return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session and not session.is_expired():
                session.update_activity()
                return session
            elif session and session.is_expired():
                # Clean up expired session
                self._cleanup_session(session_id)
            return None

    def validate_session(self, session_id: str, user_id: str = None) -> bool:
        """Validate that a session exists and belongs to the user"""
        session = self.get_session(session_id)
        if not session:
            return False
        if user_id and session.user_id != user_id:
            return False
        return True

    def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all active sessions for a user"""
        with self._lock:
            return [s for s in self._sessions.values()
                   if s.user_id == user_id and not s.is_expired()]

    def end_session(self, session_id: str):
        """End a session"""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].is_active = False
                # Clean up conversation
                if session_id in self._conversations:
                    del self._conversations[session_id]

    def _cleanup_session(self, session_id: str):
        """Clean up a session and its data"""
        if session_id in self._sessions:
            del self._sessions[session_id]
        if session_id in self._conversations:
            del self._conversations[session_id]

    def cleanup_expired_sessions(self):
        """Clean up all expired sessions"""
        with self._lock:
            expired_sessions = []
            for session_id, session in self._sessions.items():
                if session.is_expired():
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                self._cleanup_session(session_id)

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        with self._lock:
            active_sessions = sum(1 for s in self._sessions.values() if not s.is_expired())
            total_conversations = len(self._conversations)

            return {
                "active_sessions": active_sessions,
                "total_sessions": len(self._sessions),
                "total_conversations": total_conversations,
                "active_users": len(set(s.user_id for s in self._sessions.values() if not s.is_expired()))
            }

# Global conversation store instance
conversation_store = ConversationStore()