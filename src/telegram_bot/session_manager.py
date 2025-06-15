"""Session manager for handling user sessions and state."""

from typing import Dict, Optional
import asyncio
from datetime import datetime, timedelta

from .models import UserSession, UserState, TelegramUser
from ..utils.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages user sessions and conversation state."""
    
    def __init__(self, session_timeout_minutes: int = 60):
        """
        Initialize session manager.
        
        Args:
            session_timeout_minutes: Session timeout in minutes
        """
        self._sessions: Dict[int, UserSession] = {}
        self._session_timeout = timedelta(minutes=session_timeout_minutes)
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the session manager and cleanup task."""
        logger.info("Starting session manager")
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
    
    async def stop(self):
        """Stop the session manager and cleanup task."""
        logger.info("Stopping session manager")
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def get_session(self, user_id: int, chat_id: int) -> UserSession:
        """
        Get or create user session.
        
        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            
        Returns:
            UserSession: User session object
        """
        if user_id in self._sessions:
            session = self._sessions[user_id]
            session.updated_at = datetime.now()
            logger.debug(f"Retrieved existing session for user {user_id}")
            return session
        
        # Create new session
        session = UserSession(user_id=user_id, chat_id=chat_id)
        self._sessions[user_id] = session
        logger.info(f"Created new session for user {user_id}")
        return session
    
    async def get_session_by_user_id(self, user_id: int) -> Optional[UserSession]:
        """
        Get user session by user ID only.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            UserSession or None if not found
        """
        if user_id in self._sessions:
            session = self._sessions[user_id]
            session.updated_at = datetime.now()
            logger.debug(f"Retrieved session for user {user_id}")
            return session
        return None
    
    async def update_session(self, user_id: int, state: Optional[UserState] = None, 
                           context: Optional[Dict] = None, **kwargs):
        """
        Update user session.
        
        Args:
            user_id: Telegram user ID
            state: New conversation state
            context: Additional context data
            **kwargs: Additional session fields to update
        """
        if user_id not in self._sessions:
            logger.warning(f"Attempted to update non-existent session for user {user_id}")
            return
        
        session = self._sessions[user_id]
        
        if state:
            session.state = state
        
        if context:
            session.context_data.update(context)
        
        # Update other fields
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        session.updated_at = datetime.now()
        logger.debug(f"Updated session for user {user_id}, state: {session.state}")
    
    async def clear_session_context(self, user_id: int):
        """
        Clear session context data.
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self._sessions:
            self._sessions[user_id].clear_context()
            logger.debug(f"Cleared context for user {user_id}")
    
    async def delete_session(self, user_id: int):
        """
        Delete user session.
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self._sessions:
            del self._sessions[user_id]
            logger.info(f"Deleted session for user {user_id}")
    
    async def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)
    
    async def get_sessions_by_broker(self, broker_name: str) -> list[UserSession]:
        """
        Get all sessions using a specific broker.
        
        Args:
            broker_name: Broker name
            
        Returns:
            List of sessions using the broker
        """
        return [
            session for session in self._sessions.values()
            if session.selected_broker == broker_name
        ]
    
    async def _cleanup_expired_sessions(self):
        """Cleanup expired sessions periodically."""
        while True:
            try:
                now = datetime.now()
                expired_users = []
                
                for user_id, session in self._sessions.items():
                    if now - session.updated_at > self._session_timeout:
                        expired_users.append(user_id)
                
                for user_id in expired_users:
                    await self.delete_session(user_id)
                    logger.info(f"Cleaned up expired session for user {user_id}")
                
                if expired_users:
                    logger.info(f"Cleaned up {len(expired_users)} expired sessions")
                
                # Run cleanup every 5 minutes
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
                await asyncio.sleep(60)  # Wait before retrying


# Global session manager instance
session_manager = SessionManager() 