"""
AI Agent Core Module
Main loop, LLM interaction, and memory management
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

import openai
import anthropic
from dotenv import load_dotenv
import os

from .intent_router import IntentRouter
from .tool_dispatcher import ToolDispatcher
from .dialogue_handler import DialogueHandler
from .state_tracker import StateTracker

# Load environment variables
load_dotenv()

@dataclass
class AgentResponse:
    """Response structure from the agent"""
    message: str
    action_taken: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = None
    context_updated: bool = False
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.tool_calls is None:
            self.tool_calls = []

class AgentCore:
    """
    Main AI Agent Core that handles:
    - LLM interaction and reasoning
    - Tool selection and execution
    - Context and memory management
    - Main conversation loop
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize LLM client
        self.model = os.getenv("AGENT_MODEL", "gpt-4-turbo-preview")
        self.temperature = float(os.getenv("AGENT_TEMPERATURE", 0.7))
        self.max_tokens = int(os.getenv("AGENT_MAX_TOKENS", 2048))
        
        # Initialize OpenAI client (with error handling)
        try:
            self.openai_client = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY")
            )
        except Exception as e:
            self.logger.warning(f"OpenAI client initialization failed: {str(e)}")
            self.openai_client = None
        
        # Initialize Anthropic client (backup, with error handling)
        try:
            self.anthropic_client = anthropic.Anthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
        except Exception as e:
            self.logger.warning(f"Anthropic client initialization failed: {str(e)}")
            self.anthropic_client = None
        
        # Initialize core modules
        self.intent_router = IntentRouter()
        self.tool_dispatcher = ToolDispatcher()
        self.dialogue_handler = DialogueHandler()
        self.state_tracker = StateTracker()
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
        
        # Agent state
        self.is_running = False
        self.conversation_history = []
        
        self.logger.info("Agent Core initialized successfully")
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from configuration"""
        prompt_path = os.getenv("AGENT_SYSTEM_PROMPT_PATH", "agent/config/prompts/system_prompt.txt")
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            self.logger.warning(f"System prompt file not found: {prompt_path}")
            return self._get_default_system_prompt()
    
    def _get_default_system_prompt(self) -> str:
        """Default system prompt if file not found"""
        return """You are an AI assistant in a car driving through rural Yalova, Turkey. 
You can control car components (temperature, music, windows, seats), get weather information, 
play music via Spotify, and help with navigation. You should be conversational, helpful, 
and maintain context throughout the journey. Use the available tools to assist the user 
and provide a realistic in-car experience."""
    
    async def process_input(self, user_input: str) -> AgentResponse:
        """
        Main processing function for user input
        """
        try:
            self.logger.info(f"Processing user input: {user_input}")
            
            # Add user input to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Get current context
            current_context = await self.state_tracker.get_current_context()
            
            # Route intent and get recommended tools
            intent_result = await self.intent_router.route_intent(user_input, current_context)
            
            # Prepare LLM conversation with tool information
            messages = self._prepare_llm_messages(user_input, current_context, intent_result)
            
            # Get LLM response with function calling
            llm_response = await self._call_llm(messages, intent_result.get("available_tools", []))
            
            # Execute any tool calls
            tool_results = []
            if llm_response.get("tool_calls"):
                tool_results = await self._execute_tool_calls(llm_response["tool_calls"])
            
            # Generate final response
            response_message = await self._generate_final_response(
                user_input, llm_response, tool_results, current_context
            )
            
            # Update conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_message,
                "tool_calls": tool_results,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Update state tracker
            context_updated = await self.state_tracker.update_context(
                user_input, response_message, tool_results
            )
            
            # Create agent response
            agent_response = AgentResponse(
                message=response_message,
                action_taken=intent_result.get("predicted_action"),
                tool_calls=tool_results,
                context_updated=context_updated
            )
            
            # Handle dialogue (TTS, etc.)
            await self.dialogue_handler.handle_response(agent_response)
            
            return agent_response
            
        except Exception as e:
            self.logger.error(f"Error processing input: {str(e)}")
            error_response = AgentResponse(
                message="I apologize, but I encountered an issue processing your request. Please try again.",
                action_taken="error_handling"
            )
            await self.dialogue_handler.handle_response(error_response)
            return error_response
    
    def _prepare_llm_messages(self, user_input: str, context: Dict[str, Any], intent_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Prepare messages for LLM including context and history"""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add context information
        context_info = f"""
Current Context:
- Location: {context.get('location', 'Yalova, Turkey')}
- Temperature: {context.get('temperature', 22)}°C
- Music: {context.get('music_status', 'Not playing')}
- Windows: {context.get('windows', 'Closed')}
- Time: {datetime.now().strftime('%H:%M')}

Available Actions: {', '.join(intent_result.get('suggested_tools', []))}
"""
        
        messages.append({"role": "system", "content": context_info})
        
        # Add recent conversation history (last 10 exchanges)
        recent_history = self.conversation_history[-20:] if len(self.conversation_history) > 20 else self.conversation_history
        for entry in recent_history:
            messages.append({
                "role": entry["role"],
                "content": entry["content"]
            })
        
        return messages
    
    async def _call_llm(self, messages: List[Dict[str, str]], available_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call LLM with function calling support"""
        try:
            # Convert available tools to OpenAI function format
            functions = []
            for tool in available_tools:
                functions.append({
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("parameters", {})
                })
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                functions=functions if functions else None,
                function_call="auto" if functions else None
            )
            
            message = response.choices[0].message
            
            result = {
                "content": message.content,
                "tool_calls": []
            }
            
            # Handle function calls
            if message.function_call:
                result["tool_calls"].append({
                    "name": message.function_call.name,
                    "arguments": json.loads(message.function_call.arguments)
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"LLM call failed: {str(e)}")
            return {"content": "I'm having trouble processing that request right now.", "tool_calls": []}
    
    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute tool calls through the dispatcher"""
        results = []
        for tool_call in tool_calls:
            try:
                result = await self.tool_dispatcher.execute_tool(
                    tool_call["name"],
                    tool_call["arguments"]
                )
                results.append({
                    "tool": tool_call["name"],
                    "arguments": tool_call["arguments"],
                    "result": result,
                    "success": True
                })
            except Exception as e:
                self.logger.error(f"Tool execution failed for {tool_call['name']}: {str(e)}")
                results.append({
                    "tool": tool_call["name"],
                    "arguments": tool_call["arguments"],
                    "result": str(e),
                    "success": False
                })
        return results
    
    async def _generate_final_response(self, user_input: str, llm_response: Dict[str, Any], 
                                     tool_results: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """Generate final response considering tool results"""
        base_response = llm_response.get("content", "")
        
        # If tools were executed, incorporate results
        if tool_results:
            successful_actions = [r for r in tool_results if r["success"]]
            if successful_actions:
                # Let the LLM know about successful actions
                action_summary = ", ".join([f"{r['tool']} executed successfully" for r in successful_actions])
                base_response += f" I've {action_summary} for you."
        
        return base_response
    
    async def start_agent(self):
        """Start the agent main loop"""
        self.is_running = True
        self.logger.info("Agent started and ready for interaction")
        
        # Initialize simulation session
        await self.tool_dispatcher.execute_tool("start_simulation", {})
        
        # Initial greeting
        greeting = await self.dialogue_handler.get_greeting()
        await self.dialogue_handler.speak(greeting)
    
    async def stop_agent(self):
        """Stop the agent gracefully"""
        self.is_running = False
        self.logger.info("Agent stopping...")
        
        # Save conversation history
        await self.state_tracker.save_conversation_history(self.conversation_history)
        
        # End simulation session
        await self.tool_dispatcher.execute_tool("pause_simulation", {})
        
        self.logger.info("Agent stopped successfully")
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get current conversation history"""
        return self.conversation_history.copy()
    
    async def reset_conversation(self):
        """Reset conversation and context"""
        self.conversation_history = []
        await self.state_tracker.reset_context()
        await self.tool_dispatcher.execute_tool("reset_simulation", {})
        self.logger.info("Conversation and context reset")
