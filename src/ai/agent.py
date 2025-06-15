"""AI Trading Agent using OpenAI."""

import json
import re
import asyncio
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
import structlog
from openai import AsyncOpenAI

from .tools import ToolRegistry, BrokerTools, TOOL_FUNCTIONS
from .prompts import PromptManager
from ..brokers.angelone import AngelOneBroker
from ..config import settings
from ..telegram_bot.broker_manager import broker_manager

logger = structlog.get_logger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal objects."""
    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class AIAgent:
    """AI-powered trading agent using OpenAI and AngelOne broker."""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.broker = None
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.tools = BrokerTools(user_id)
        self.prompts = PromptManager()
        self.conversation_history: List[Dict[str, Any]] = []
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}
        self.max_history_messages = 20  # Limit conversation history
    
    async def process_message(self, user_message: str) -> str:
        """Process user message and return AI response."""
        try:
            # Clean old history
            self._clean_conversation_history()
            
            # Check for greeting messages first
            greeting_response = await self._handle_greetings(user_message)
            if greeting_response:
                return greeting_response
            
            # Check for pending confirmations
            confirmation_response = await self._handle_confirmations(user_message)
            if confirmation_response:
                return confirmation_response
            
            # Check if we need to include conversation history
            include_history = await self._should_include_history(user_message)
            
            # Prepare messages for the API
            if include_history and self.conversation_history:
                # Include conversation history
                messages = self.conversation_history.copy()
                messages.append({"role": "user", "content": user_message})
            else:
                # Fresh conversation - only system prompt and current message
                available_tools = "\n".join([f"- {tool['function']['name']}: {tool['function']['description']}" 
                                           for tool in TOOL_FUNCTIONS])
                system_prompt = self.prompts.get_prompt("trading_assistant", available_tools=available_tools)
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            
            logger.info(f"Making OpenAI API call with {len(messages)} messages and {len(TOOL_FUNCTIONS)} tools")
            
            # Make OpenAI API call
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_FUNCTIONS,
                temperature=0.1
            )
            
            assistant_message = response.choices[0].message
            
            # Handle tool calls
            if assistant_message.tool_calls:
                logger.info(f"Assistant made {len(assistant_message.tool_calls)} tool calls")
                
                # Add the assistant's message with tool calls to conversation
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                        for tool_call in assistant_message.tool_calls
                    ]
                })
                
                # Execute tools
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Executing tool: {function_name} with args: {function_args}")
                    
                    # Execute the tool using BrokerTools
                    if hasattr(self.tools, function_name):
                        tool_function = getattr(self.tools, function_name)
                        tool_result = await tool_function(**function_args)
                        logger.info(f"Tool {function_name} result: {tool_result}")
                    else:
                        tool_result = {"error": f"Unknown function: {function_name}"}
                        logger.error(f"Unknown function called: {function_name}")
                    
                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result, cls=DecimalEncoder)
                    })
                
                # Get final response from OpenAI
                final_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1
                )
                
                final_message = final_response.choices[0].message.content
            else:
                final_message = assistant_message.content
                logger.info("No tool calls made by assistant")
            
            # Update conversation history
            if include_history:
                # Add both user message and assistant response to ongoing conversation
                if not any(msg["role"] == "user" and msg["content"] == user_message 
                         for msg in self.conversation_history[-2:]):
                    self.conversation_history.append({"role": "user", "content": user_message})
                self.conversation_history.append({"role": "assistant", "content": final_message})
            else:
                # Start fresh conversation history with system message
                available_tools = "\n".join([f"- {tool['function']['name']}: {tool['function']['description']}" 
                                           for tool in TOOL_FUNCTIONS])
                system_prompt = self.prompts.get_prompt("trading_assistant", available_tools=available_tools)
                self.conversation_history = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": final_message}
                ]
            
            return final_message
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return "I encountered a technical issue. Please try again or use specific commands like /funds, /holdings, etc."
    
    async def _handle_greetings(self, user_message: str) -> Optional[str]:
        """Handle greeting messages with comprehensive examples."""
        user_lower = user_message.lower().strip()
        
        # Exclude trading-related keywords even in greeting-like messages
        trading_keywords = [
            'price', 'quote', 'ltp', 'buy', 'sell', 'stock', 'share', 'holding', 
            'position', 'order', 'fund', 'balance', 'profit', 'loss', 'trade',
            'market', 'nse', 'bse', 'intraday', 'delivery'
        ]
        
        # Check if it contains trading keywords
        has_trading_keywords = any(keyword in user_lower for keyword in trading_keywords)
        
        # Pure greeting patterns
        greeting_patterns = [
            r'^(hi|hello|hey|hii+|hello+)$',
            r'^(hi|hello|hey)\s*(there|bot|assistant)?$',
            r'^good\s+(morning|afternoon|evening|day)$',
            r'^what\s+can\s+you\s+do(\?|\s*for\s+me\?)?$',
            r'^help\s*me$',
            r'^(can\s+you\s+)?help(\?)?$'
        ]
        
        # Only trigger greeting if it matches patterns AND doesn't have trading keywords
        is_greeting = any(re.match(pattern, user_lower) for pattern in greeting_patterns)
        
        if is_greeting and not has_trading_keywords:
            # Get broker to fetch auth status and funds
            broker = await broker_manager.get_broker(self.user_id)
            
            if broker:
                auth_status = "✅ Connected to AngelOne"
                try:
                    funds_response = await broker.get_funds()
                    if funds_response.success:
                        available_funds = f"₹{funds_response.data.get('availableCash', 0):,.2f}"
                    else:
                        available_funds = "Not available"
                except:
                    available_funds = "Not available"
            else:
                auth_status = "❌ Not connected - Use /broker to connect"
                available_funds = "Not available"
            
            return self.prompts.get_prompt(
                "greeting",
                auth_status=auth_status
            )
        
        return None
    
    async def _should_include_history(self, user_message: str) -> bool:
        """Determine if conversation history should be included based on user message."""
        # Keywords that suggest the user needs context from previous conversation
        context_requiring_keywords = [
            "continue", "also", "too", "and", "more", "else", "other", "again",
            "what about", "how about", "similarly", "likewise", "additionally",
            "furthermore", "moreover", "besides", "it", "that", "this", "they", "them"
        ]
        
        # Commands that are standalone and don't need history
        standalone_commands = [
            "balance", "funds", "quote", "price", "holdings", "positions", "orders",
            "buy", "sell", "hello", "hi", "help", "what can you do", "profile"
        ]
        
        user_lower = user_message.lower()
        
        # Check if message contains context-requiring keywords
        has_context_keywords = any(keyword in user_lower for keyword in context_requiring_keywords)
        
        # Check if it's a standalone command
        is_standalone = any(command in user_lower for command in standalone_commands)
        
        # Include history if:
        # 1. Message has context keywords AND it's not a simple standalone command
        # 2. Or if conversation history is short (user might be building context)
        return (has_context_keywords and not is_standalone) or len(self.conversation_history) <= 4
    
    def _clean_conversation_history(self):
        """Clean old conversation history to keep it manageable."""
        if len(self.conversation_history) > self.max_history_messages:
            # Keep the system message and recent messages
            system_messages = [msg for msg in self.conversation_history if msg["role"] == "system"]
            recent_messages = self.conversation_history[-(self.max_history_messages-1):]
            self.conversation_history = system_messages + recent_messages
    
    async def _handle_confirmations(self, user_message: str) -> Optional[str]:
        """Handle pending confirmations."""
        message_upper = user_message.upper().strip()
        
        if message_upper in ["CONFIRM", "YES", "Y"]:
            # Execute pending confirmation
            pending = None
            for conf_id, conf_data in self.pending_confirmations.items():
                if conf_data["user_id"] == self.user_id:
                    pending = conf_data
                    del self.pending_confirmations[conf_id]
                    break
            
            if pending:
                result = await self.tools.execute_tool(
                    pending["function_name"], 
                    pending["function_args"]
                )
                
                if result.get("success"):
                    return f"✅ Trade executed successfully!\n\nDetails: {json.dumps(result['data'], indent=2, cls=DecimalEncoder)}"
                else:
                    return f"❌ Trade execution failed: {result.get('error', 'Unknown error')}"
            else:
                return "❌ No pending confirmation found."
        
        elif message_upper in ["CANCEL", "NO", "N"]:
            # Cancel pending confirmation
            for conf_id, conf_data in list(self.pending_confirmations.items()):
                if conf_data["user_id"] == self.user_id:
                    del self.pending_confirmations[conf_id]
                    return "❌ Trade cancelled."
            
            return "❌ No pending confirmation to cancel."
        
        return None
    
    def clear_conversation(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        logger.info(f"Conversation history cleared for user {self.user_id}")
    
    def get_conversation_summary(self) -> str:
        """Get summary of recent conversation."""
        if not self.conversation_history:
            return "No recent conversation."
        
        recent_messages = self.conversation_history[-6:]  # Last 3 exchanges
        summary = []
        
        for msg in recent_messages:
            role = msg["role"]
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            summary.append(f"{role.title()}: {content}")
        
        return "\n".join(summary)


class AIHandler:
    """Handler for AI interactions."""
    
    def __init__(self):
        self.agents: Dict[int, AIAgent] = {}
    
    async def get_or_create_agent(self, user_id: int) -> Optional[AIAgent]:
        """Get or create AI agent for user."""
        # First try to get existing broker
        broker = await broker_manager.get_broker(user_id)
        
        # If no broker found, try to create one
        if not broker:
            logger.info(f"No broker found for user {user_id}, attempting to create one")
            broker = await broker_manager.get_or_create_broker(user_id)
            
        if not broker:
            logger.warning(f"Failed to get or create broker for user {user_id}")
            return None
        
        if user_id not in self.agents:
            self.agents[user_id] = AIAgent(user_id)
            logger.info(f"Created AI agent for user {user_id}")
        
        return self.agents[user_id]
    
    async def handle_ai_message(self, update, context):
        """Handle AI message processing."""
        user_id = update.effective_user.id
        user_message = update.message.text
        
        try:
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            agent = await self.get_or_create_agent(user_id)
            if not agent:
                await update.message.reply_text(
                    "❌ Please connect to a broker first using /broker command."
                )
                return
            
            # Process message
            response = await agent.process_message(user_message)
            
            # Send response
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in AI handler: {e}")
            await update.message.reply_text(
                "I encountered an error. Please try again or use specific commands."
            )
    
    async def clear_conversation(self, user_id: int):
        """Clear conversation for user."""
        if user_id in self.agents:
            self.agents[user_id].clear_conversation()
    
    def remove_agent(self, user_id: int):
        """Remove agent for user."""
        if user_id in self.agents:
            del self.agents[user_id]
            logger.info(f"Removed AI agent for user {user_id}")


# Global AI handler instance
ai_handler = AIHandler() 