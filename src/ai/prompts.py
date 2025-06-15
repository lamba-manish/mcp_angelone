"""Prompt management for AI trading agent."""

from typing import Dict, List, Any
from dataclasses import dataclass
import json


@dataclass
class PromptTemplate:
    """Represents a prompt template."""
    name: str
    template: str
    description: str
    variables: List[str]


class PromptManager:
    """Manages prompts for different trading scenarios."""
    
    def __init__(self):
        self.prompts = self._load_prompts()
    
    def _load_prompts(self) -> Dict[str, PromptTemplate]:
        """Load predefined prompts."""
        prompts = {}
        
        # System prompt for the trading agent
        prompts["system"] = PromptTemplate(
            name="system",
            template="""You are an advanced AI trading assistant with access to AngelOne broker APIs and real-time market data. Your role is to help users with their trading activities through natural language conversations.

## Your Capabilities:
1. **Account Management**: Check account details, funds, margins
2. **Market Data**: Get live quotes, market depth, historical data, charts
3. **Portfolio Management**: View holdings, positions, order history
4. **Trade Execution**: Place buy/sell orders, modify/cancel orders
5. **Market Analysis**: Top gainers/losers, market trends, comparisons
6. **Web Search**: Search for additional market information when needed

## Available Tools:
{available_tools}

## Guidelines:
1. Always confirm high-risk actions (selling, large orders) before execution
2. Provide clear explanations of market data and recommendations
3. Ask for clarification when user intent is ambiguous
4. Use tools efficiently to gather necessary information
5. Format responses clearly with appropriate emojis and structure
6. Never execute trades without explicit user confirmation
7. Always mention risks associated with trading decisions

## Current User Context:
- Broker: AngelOne
- Authentication Status: {auth_status}
- Available Funds: {available_funds}

Respond naturally and helpfully to user queries. Use tools as needed to provide accurate, up-to-date information.""",
            description="Main system prompt for the trading agent",
            variables=["available_tools", "auth_status", "available_funds"]
        )
        
        # Tool selection prompt
        prompts["tool_selection"] = PromptTemplate(
            name="tool_selection",
            template="""Based on the user's query: "{user_query}"

Analyze what the user wants to accomplish and select the most appropriate tools to use.

Available tools:
{available_tools}

Current context:
{context}

What tools should be used and in what order? Provide a brief reasoning.""",
            description="Helps select appropriate tools for user queries",
            variables=["user_query", "available_tools", "context"]
        )
        
        # Market analysis prompt
        prompts["market_analysis"] = PromptTemplate(
            name="market_analysis",
            template="""Analyze the following market data for {symbol}:

Current Quote: {quote_data}
Holdings: {holdings_data}
Market Depth: {market_depth}
Recent Performance: {performance_data}

Provide a comprehensive analysis including:
1. Current price and trend analysis
2. Support and resistance levels
3. Volume analysis
4. Comparison with user's holdings (if applicable)
5. Trading recommendations with risk assessment

Use clear formatting with emojis for better readability.""",
            description="Analyzes market data and provides insights",
            variables=["symbol", "quote_data", "holdings_data", "market_depth", "performance_data"]
        )
        
        # Trade confirmation prompt
        prompts["trade_confirmation"] = PromptTemplate(
            name="trade_confirmation",
            template="""🚨 **TRADE CONFIRMATION REQUIRED** 🚨

You are about to execute the following trade:
- **Action**: {action}
- **Symbol**: {symbol}
- **Quantity**: {quantity}
- **Price**: {price} ({order_type})
- **Estimated Value**: ₹{estimated_value:,.2f}

**Current Market Data**:
- Last Price: ₹{current_price}
- Available Funds: ₹{available_funds:,.2f}

**Risk Assessment**:
{risk_assessment}

Please confirm if you want to proceed with this trade by responding with "CONFIRM" or cancel with "CANCEL".""",
            description="Confirms trade execution with user",
            variables=["action", "symbol", "quantity", "price", "order_type", "estimated_value", "current_price", "available_funds", "risk_assessment"]
        )
        
        # Error handling prompt
        prompts["error_handling"] = PromptTemplate(
            name="error_handling",
            template="""An error occurred while processing your request:

**Error**: {error_message}
**Context**: {context}

**Possible Solutions**:
{suggestions}

Would you like me to:
1. Try an alternative approach
2. Provide more information about the error
3. Help you with something else

Please let me know how you'd like to proceed.""",
            description="Handles errors gracefully",
            variables=["error_message", "context", "suggestions"]
        )
        
        # Trading assistant system prompt (for fresh conversations)
        prompts["trading_assistant"] = PromptTemplate(
            name="trading_assistant",
            template="""You are an AI trading assistant with access to AngelOne broker APIs. Help users with their trading needs through natural conversation.

## Your Capabilities:
- Account management (funds, profile, margins)
- Live market data (quotes, prices, market depth)
- Portfolio management (holdings, positions, orders)
- Trade execution (buy/sell orders with confirmations)
- Market analysis (top gainers/losers, trends)

## Tools Available:
{available_tools}

## Guidelines:
1. Always confirm trades before execution
2. Provide clear market data explanations
3. Ask for clarification when needed
4. Format responses with emojis and structure
5. Mention risks for trading decisions

Respond naturally and helpfully to user queries. Use tools to provide accurate, real-time information.""",
            description="System prompt for fresh trading conversations",
            variables=["available_tools"]
        )

        # Greeting and help prompt
        prompts["greeting"] = PromptTemplate(
            name="greeting",
            template="""👋 **Hello! I'm your AI Trading Assistant!**

I'm here to help you with all your trading needs using natural language. Here's what I can do for you:

## 🚀 **What I Can Help With:**

### 💰 **Account & Funds**
- "What's my balance?" / "Show me my available funds"
- "Check my margins" / "Account details"

### 📈 **Market Data & Quotes**
- "RELIANCE live price" / "What's the current price of RELIANCE?"
- "ITC LTP" / "Show me ITC quote"
- "Market depth for TCS" / "Order book for HDFC"

### 📊 **Portfolio Management**
- "Show my holdings" / "What stocks do I own?"
- "My current positions" / "Today's orders"
- "Portfolio summary" / "P&L status"

### 🛒 **Trading Operations**
- "Buy 10 shares of RELIANCE at 2500" 
- "Sell 5 TCS shares at market price"
- "Place a limit order for ITC"
- "Cancel my pending orders"

### 📋 **Market Analysis**
- "Top gainers today" / "Top losers"
- "Compare HDFC vs ICICI bank"
- "Show me NIFTY chart"

### 🔍 **Search & Research**
- "Search for automobile stocks"
- "Tell me about Tata Motors"
- "Market news about pharma sector"

## 💡 **Quick Examples:**
Just type naturally like:
- "What's my balance?"
- "RELIANCE price please"
- "Buy 1 ITC share"
- "Show top gainers"
- "What's my portfolio worth?"

## ⚡ **Pro Tips:**
- I understand both formal and casual language
- For orders, I'll always ask for confirmation before executing
- I can explain market terms and provide analysis
- Use `/ai` to toggle AI mode on/off

**Current Status**: {auth_status}

How can I assist you today? 🤝""",
            description="Greeting message with examples and capabilities",
            variables=["auth_status"]
        )

        # Quick help for AI mode
        prompts["ai_help"] = PromptTemplate(
            name="ai_help",
            template="""🤖 **AI Assistant Mode Activated!**

You can now chat with me naturally! Here are some examples:

**📈 Market Queries:**
• "RELIANCE current price"
• "Show me TCS quote"
• "What's ITC trading at?"
• "Top gainers today"

**💰 Account & Portfolio:**
• "What's my balance?"
• "Show my holdings"
• "Current positions"
• "Today's orders"

**🛒 Trading:**
• "Buy 10 RELIANCE shares"
• "Sell 5 TCS at 3800"
• "Place order for ITC"

**📊 Analysis:**
• "Compare HDFC vs ICICI"
• "Market depth for SBIN"
• "NIFTY performance"

Just type your question naturally - I'll understand! 🚀

**Status**: {auth_status}""",
            description="Help message for AI mode activation",
            variables=["auth_status"]
        )
        
        return prompts
    
    def get_prompt(self, name: str, **kwargs) -> str:
        """Get a formatted prompt by name."""
        if name not in self.prompts:
            raise ValueError(f"Prompt '{name}' not found")
        
        template = self.prompts[name].template
        
        # Replace variables
        try:
            return template.format(**kwargs)
        except KeyError as e:
            missing_var = str(e).strip("'")
            raise ValueError(f"Missing variable '{missing_var}' for prompt '{name}'")
    
    def list_prompts(self) -> List[str]:
        """List available prompt names."""
        return list(self.prompts.keys())
    
    def get_prompt_info(self, name: str) -> PromptTemplate:
        """Get information about a specific prompt."""
        if name not in self.prompts:
            raise ValueError(f"Prompt '{name}' not found")
        return self.prompts[name]
    
    def add_custom_prompt(self, name: str, template: str, description: str, variables: List[str]):
        """Add a custom prompt template."""
        self.prompts[name] = PromptTemplate(
            name=name,
            template=template,
            description=description,
            variables=variables
        ) 