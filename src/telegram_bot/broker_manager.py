"""Centralized broker management for sharing instances between AI and traditional handlers."""

import asyncio
from typing import Dict, Optional
import structlog

from ..brokers.angelone import AngelOneBroker
from .session_manager import session_manager
from .models import UserState

logger = structlog.get_logger(__name__)


class BrokerManager:
    """Centralized broker instance management."""
    
    def __init__(self):
        self.broker_instances: Dict[int, AngelOneBroker] = {}  # user_id -> broker
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the broker manager."""
        logger.info("Starting broker manager")
        self._cleanup_task = asyncio.create_task(self._cleanup_inactive_brokers())
    
    async def stop(self):
        """Stop the broker manager."""
        logger.info("Stopping broker manager")
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Logout all brokers
        for broker in self.broker_instances.values():
            try:
                await broker.logout()
            except:
                pass  # Ignore logout errors during shutdown
        
        self.broker_instances.clear()
    
    async def get_or_create_broker(self, user_id: int) -> Optional[AngelOneBroker]:
        """Get existing broker or create new one for user."""
        # Return existing broker if available and valid
        if user_id in self.broker_instances:
            broker = self.broker_instances[user_id]
            # Verify broker is still valid
            try:
                profile_response = await broker.get_profile()
                if profile_response.success:
                    logger.debug(f"Returning existing broker for user {user_id}")
                    return broker
                else:
                    logger.warning(f"Existing broker for user {user_id} is invalid, creating new one")
                    await self._remove_broker(user_id)
            except Exception as e:
                logger.warning(f"Error validating existing broker for user {user_id}: {e}")
                await self._remove_broker(user_id)
        
        # Create new broker and attempt authentication
        try:
            broker = AngelOneBroker()
            login_response = await broker.login()
            
            if login_response.success:
                self.broker_instances[user_id] = broker
                logger.info(f"Created and authenticated broker for user {user_id}")
                
                # Update session to authenticated after successful broker creation
                # First ensure session exists (create with dummy chat_id if needed)
                session = await session_manager.get_session_by_user_id(user_id)
                if not session:
                    # Create session with user_id as chat_id (for private chats they're the same)
                    session = await session_manager.get_session(user_id, user_id)
                
                await session_manager.update_session(
                    user_id,
                    state=UserState.AUTHENTICATED,
                    broker_authenticated=True
                )
                
                return broker
            else:
                logger.error(f"Failed to authenticate new broker for user {user_id}: {login_response.message}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating broker for user {user_id}: {e}")
            return None
    
    async def get_broker(self, user_id: int) -> Optional[AngelOneBroker]:
        """Get existing broker for user (don't create new one)."""
        return self.broker_instances.get(user_id)
    
    async def remove_broker(self, user_id: int):
        """Remove broker for user (e.g., on logout)."""
        await self._remove_broker(user_id)
    
    async def _remove_broker(self, user_id: int):
        """Internal method to remove broker."""
        if user_id in self.broker_instances:
            broker = self.broker_instances[user_id]
            try:
                await broker.logout()
            except:
                pass  # Ignore logout errors
            del self.broker_instances[user_id]
            logger.info(f"Removed broker for user {user_id}")
    
    async def _cleanup_inactive_brokers(self):
        """Cleanup brokers for inactive sessions."""
        while True:
            try:
                await asyncio.sleep(1800)  # Check every 30 minutes (more lenient)
                
                inactive_users = []
                for user_id in list(self.broker_instances.keys()):
                    try:
                        # Test broker validity by trying to get profile
                        broker = self.broker_instances[user_id]
                        profile_response = await broker.get_profile()
                        
                        # Only remove if broker is clearly invalid
                        if not profile_response.success:
                            logger.warning(f"Broker for user {user_id} is invalid: {profile_response.message}")
                            inactive_users.append(user_id)
                    except Exception as e:
                        logger.warning(f"Error checking broker for user {user_id}: {e}")
                        # Don't remove on error, could be temporary network issue
                        continue
                
                for user_id in inactive_users:
                    await self._remove_broker(user_id)
                    logger.info(f"Cleaned up invalid broker for user {user_id}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in broker cleanup: {e}")
                await asyncio.sleep(300)  # Wait before retrying
    
    def get_active_broker_count(self) -> int:
        """Get count of active brokers."""
        return len(self.broker_instances)


# Global broker manager instance
broker_manager = BrokerManager() 