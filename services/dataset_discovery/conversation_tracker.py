"""
Conversation tracker for dataset analysis that integrates with the enhanced chat service
"""
import logging
import time
from typing import Dict, Any, Optional
from services.enhanced_chat_service import EnhancedChatService

logger = logging.getLogger(__name__)

# Global in-memory store for conversations
_conversation_store = {}


class ConversationTracker:
    """Track model conversations during dataset analysis."""
    
    def __init__(self, save_to_db: bool = False, auto_cleanup: bool = True):
        """
        Initialize conversation tracker.
        
        Args:
            save_to_db: Whether to save to Firestore (default: False for cost savings)
            auto_cleanup: Whether to delete conversation after analysis (default: True)
        """
        self.chat_service = EnhancedChatService()
        self.save_to_db = save_to_db
        self.auto_cleanup = auto_cleanup
        self.conversation_id = None
        self.conversation_data = None
        self.messages = []  # In-memory message store
        
    def create_conversation(self, user_id: str = "analysis_system", 
                          user_email: str = "system@phoenix.ai", 
                          title: str = "Dataset Analysis") -> str:
        """Create a new conversation for the analysis."""
        try:
            if self.save_to_db:
                # Create in Firestore
                result = self.chat_service.create_conversation(
                    user_id=user_id,
                    user_email=user_email,
                    origin="dataset_analysis",
                    title=title
                )
                self.conversation_id = result["conversation_id"]
                self.conversation_data = result
                logger.info(f"💾 Created conversation in Firestore: {self.conversation_id}")
            else:
                # Create in-memory only
                import uuid
                self.conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
                self.conversation_data = {
                    "conversation_id": self.conversation_id,
                    "title": title,
                    "origin": "dataset_analysis",
                    "user_id": user_id,
                    "user_email": user_email,
                    "created_at": time.time(),
                    "in_memory": True
                }
                self.messages = []
                
                # Store in global store
                _conversation_store[self.conversation_id] = {
                    "data": self.conversation_data,
                    "messages": self.messages
                }
                
                logger.info(f"🧠 Created in-memory conversation: {self.conversation_id}")
                
            return self.conversation_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create conversation: {e}")
            # Fallback to in-memory
            import uuid
            self.conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
            self.conversation_data = {"conversation_id": self.conversation_id, "in_memory": True}
            self.messages = []
            return self.conversation_id
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Add a message to the conversation.
        
        Args:
            role: "user" (prompt to model) or "assistant" (model response)
            content: Message content
            metadata: Additional metadata (tokens, timing, etc.)
            
        Returns:
            Message data
        """
        try:
            message_data = {
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "timestamp": time.time(),
                "conversation_id": self.conversation_id
            }
            
            if self.save_to_db and self.conversation_id:
                # Save to Firestore
                result = self.chat_service.create_message(
                    conversation_id=self.conversation_id,
                    user_id=self.conversation_data.get("user_id", "analysis_system"),
                    role=role,
                    content=content,
                    model_info=metadata
                )
                message_data.update(result)
                logger.info(f"💾 Saved message to Firestore: {role}")
            else:
                # Store in-memory
                import uuid
                message_data["message_id"] = f"msg_{uuid.uuid4().hex[:8]}"
                self.messages.append(message_data)
                
                # Update global store
                if self.conversation_id and self.conversation_id in _conversation_store:
                    _conversation_store[self.conversation_id]["messages"] = self.messages
                
                logger.info(f"🧠 Added in-memory message: {role}")
            
            return message_data
            
        except Exception as e:
            logger.error(f"❌ Failed to add message: {e}")
            # Fallback to in-memory
            import uuid
            message_data = {
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "conversation_id": self.conversation_id,
                "in_memory": True
            }
            self.messages.append(message_data)
            return message_data
    
    def get_messages(self) -> list:
        """Get all messages in the conversation."""
        if self.save_to_db and self.conversation_id:
            try:
                return self.chat_service.get_conversation_messages(
                    conversation_id=self.conversation_id,
                    user_id=self.conversation_data.get("user_id", "analysis_system")
                )
            except Exception as e:
                logger.error(f"❌ Failed to get messages from Firestore: {e}")
                return self.messages
        else:
            # Check global store if this is a fresh instance
            if self.conversation_id and self.conversation_id in _conversation_store:
                return _conversation_store[self.conversation_id]["messages"]
            return self.messages
    
    def add_user_prompt(self, step: int, iteration: int, task_description: str, 
                       code_type: str = "initial") -> Dict[str, Any]:
        """Add a user prompt (request to model)."""
        title = f"Step {step} - {code_type.title()} Code Generation (Iteration {iteration})"
        content = f"Task: {task_description}"
        
        return self.add_message("user", content, {
            "step": step,
            "iteration": iteration,
            "code_type": code_type,
            "title": title
        })
    
    def add_model_response(self, step: int, iteration: int, success: bool, 
                          output: str = "", error: str = "", execution_time: float = 0,
                          generation_time: float = 0, tokens: Dict[str, int] = None, 
                          code: str = "") -> Dict[str, Any]:
        """Add a model response."""
        status = "✅ Success" if success else "❌ Failed"
        title = f"Step {step} Iteration {iteration} - {status}"
        
        content = output if success else f"Error: {error}"
        
        return self.add_message("assistant", content, {
            "step": step,
            "iteration": iteration,
            "success": success,
            "execution_time": execution_time,
            "generation_time": generation_time,
            "tokens": tokens or {},
            "title": title,
            "status": status,
            "code": code  # Include code in metadata
        })
    
    def cleanup_conversation(self) -> bool:
        """Clean up the conversation (delete from Firestore if enabled)."""
        if not self.auto_cleanup:
            logger.info("🔧 Auto-cleanup disabled, keeping conversation")
            return True
            
        try:
            if self.save_to_db and self.conversation_id:
                # Delete from Firestore
                success = self.chat_service.delete_conversation(
                    conversation_id=self.conversation_id,
                    user_id=self.conversation_data.get("user_id", "analysis_system")
                )
                if success:
                    logger.info(f"🗑️ Deleted conversation from Firestore: {self.conversation_id}")
                return success
            else:
                # Clear in-memory data
                self.messages.clear()
                self.conversation_data = None
                self.conversation_id = None
                logger.info("🗑️ Cleared in-memory conversation")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to cleanup conversation: {e}")
            return False
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversation."""
        messages = self.get_messages()
        
        user_messages = [m for m in messages if m.get("role") == "user"]
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        
        total_tokens = 0
        for msg in messages:
            tokens = msg.get("metadata", {}).get("tokens", {})
            total_tokens += tokens.get("input", 0) + tokens.get("output", 0)
        
        return {
            "conversation_id": self.conversation_id,
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "total_tokens": total_tokens,
            "saved_to_db": self.save_to_db,
            "in_memory": not self.save_to_db
        }
    
    @staticmethod
    def get_conversation_by_id(conversation_id: str) -> Optional['ConversationTracker']:
        """Get a conversation from the global store by ID."""
        if conversation_id in _conversation_store:
            tracker = ConversationTracker(save_to_db=False, auto_cleanup=False)
            tracker.conversation_id = conversation_id
            tracker.conversation_data = _conversation_store[conversation_id]["data"]
            tracker.messages = _conversation_store[conversation_id]["messages"]
            return tracker
        return None