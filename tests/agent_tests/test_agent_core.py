"""
Tests for Agent Core Module
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Mock the external dependencies
sys.modules['openai'] = Mock()
sys.modules['anthropic'] = Mock()
sys.modules['dotenv'] = Mock()
sys.modules['httpx'] = Mock()
sys.modules['pyttsx3'] = Mock()

from agent.agent_core import AgentCore, AgentResponse
from agent.intent_router import IntentRouter, IntentType
from agent.tool_dispatcher import ToolDispatcher
from agent.dialogue_handler import DialogueHandler
from agent.state_tracker import StateTracker

class TestAgentCore:
    """Test cases for AgentCore"""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.function_call = None
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client
    
    @pytest.fixture
    def agent_core(self, mock_openai_client):
        """Create AgentCore instance with mocked dependencies"""
        with patch.dict(os.environ, {
            'AGENT_MODEL': 'gpt-4-turbo-preview',
            'AGENT_TEMPERATURE': '0.7',
            'AGENT_MAX_TOKENS': '2048',
            'OPENAI_API_KEY': 'test-key'
        }):
            with patch('agent.agent_core.openai.OpenAI', return_value=mock_openai_client):
                agent = AgentCore()
                return agent
    
    def test_agent_core_initialization(self, agent_core):
        """Test AgentCore initialization"""
        assert agent_core is not None
        assert agent_core.model == 'gpt-4-turbo-preview'
        assert agent_core.temperature == 0.7
        assert agent_core.max_tokens == 2048
        assert isinstance(agent_core.intent_router, IntentRouter)
        assert isinstance(agent_core.tool_dispatcher, ToolDispatcher)
        assert isinstance(agent_core.dialogue_handler, DialogueHandler)
        assert isinstance(agent_core.state_tracker, StateTracker)
    
    def test_load_system_prompt_default(self, agent_core):
        """Test loading default system prompt when file not found"""
        prompt = agent_core._get_default_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "AI assistant" in prompt.lower() or "yalova" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_process_input_basic(self, agent_core, mock_openai_client):
        """Test basic input processing"""
        # Mock the dependencies
        agent_core.state_tracker.get_current_context = AsyncMock(return_value={
            "environment": {"temperature": 22},
            "preferences": {"language": "en"}
        })
        agent_core.intent_router.route_intent = AsyncMock(return_value={
            "intent_type": "conversation",
            "confidence": 0.8,
            "suggested_tools": ["talk"],
            "available_tools": [{"name": "talk", "description": "Talk to user"}],
            "extracted_parameters": {},
            "predicted_action": "conversation"
        })
        agent_core.state_tracker.update_context = AsyncMock(return_value=True)
        agent_core.dialogue_handler.handle_response = AsyncMock()
        
        user_input = "Hello, how are you?"
        response = await agent_core.process_input(user_input)
        
        assert isinstance(response, AgentResponse)
        assert response.message is not None
        assert len(agent_core.conversation_history) > 0
    
    @pytest.mark.asyncio
    async def test_process_input_with_tool_calls(self, agent_core, mock_openai_client):
        """Test input processing with tool calls"""
        # Mock function call response
        mock_openai_client.chat.completions.create.return_value.choices[0].message.function_call = Mock()
        mock_openai_client.chat.completions.create.return_value.choices[0].message.function_call.name = "set_temperature"
        mock_openai_client.chat.completions.create.return_value.choices[0].message.function_call.arguments = '{"temperature": 24}'
        
        agent_core.tool_dispatcher.execute_tool = AsyncMock(return_value={
            "success": True,
            "message": "Temperature set to 24°C"
        })
        agent_core.state_tracker.get_current_context = AsyncMock(return_value={})
        agent_core.intent_router.route_intent = AsyncMock(return_value={
            "intent_type": "temperature_control",
            "confidence": 0.9,
            "suggested_tools": ["set_temperature"],
            "available_tools": [{"name": "set_temperature", "description": "Set temperature"}],
            "extracted_parameters": {"temperature": 24},
            "predicted_action": "increase_temperature"
        })
        agent_core.state_tracker.update_context = AsyncMock(return_value=True)
        agent_core.dialogue_handler.handle_response = AsyncMock()
        
        user_input = "It's cold, set temperature to 24"
        response = await agent_core.process_input(user_input)
        
        assert isinstance(response, AgentResponse)
        assert response.action_taken == "increase_temperature"
        assert len(response.tool_calls) > 0
    
    def test_prepare_llm_messages(self, agent_core):
        """Test LLM message preparation"""
        user_input = "Test input"
        context = {"temperature": 22, "location": "Yalova"}
        intent_result = {"suggested_tools": ["talk"]}
        
        messages = agent_core._prepare_llm_messages(user_input, context, intent_result)
        
        assert isinstance(messages, list)
        assert len(messages) >= 2  # System prompt + context
        assert messages[0]["role"] == "system"
    
    @pytest.mark.asyncio
    async def test_start_and_stop_agent(self, agent_core):
        """Test agent startup and shutdown"""
        agent_core.tool_dispatcher.execute_tool = AsyncMock(return_value={"success": True})
        agent_core.dialogue_handler.get_greeting = AsyncMock(return_value="Hello!")
        agent_core.dialogue_handler.speak = AsyncMock()
        agent_core.state_tracker.save_conversation_history = AsyncMock()
        
        await agent_core.start_agent()
        assert agent_core.is_running is True
        
        await agent_core.stop_agent()
        assert agent_core.is_running is False
    
    @pytest.mark.asyncio
    async def test_reset_conversation(self, agent_core):
        """Test conversation reset"""
        agent_core.conversation_history = [{"test": "data"}]
        agent_core.state_tracker.reset_context = AsyncMock()
        agent_core.tool_dispatcher.execute_tool = AsyncMock()
        
        await agent_core.reset_conversation()
        
        assert len(agent_core.conversation_history) == 0
    
    def test_get_conversation_history(self, agent_core):
        """Test getting conversation history"""
        agent_core.conversation_history = [{"test": "data"}]
        history = agent_core.get_conversation_history()
        
        assert isinstance(history, list)
        assert len(history) == 1
        assert history[0]["test"] == "data"
        # Ensure it's a copy, not the original
        assert history is not agent_core.conversation_history

class TestAgentResponse:
    """Test cases for AgentResponse dataclass"""
    
    def test_agent_response_creation(self):
        """Test AgentResponse creation"""
        response = AgentResponse(
            message="Test message",
            action_taken="test_action"
        )
        
        assert response.message == "Test message"
        assert response.action_taken == "test_action"
        assert response.tool_calls == []
        assert response.context_updated is False
        assert isinstance(response.timestamp, datetime)
    
    def test_agent_response_with_tool_calls(self):
        """Test AgentResponse with tool calls"""
        tool_calls = [{"tool": "test_tool", "result": "success"}]
        response = AgentResponse(
            message="Test message",
            tool_calls=tool_calls,
            context_updated=True
        )
        
        assert response.tool_calls == tool_calls
        assert response.context_updated is True

if __name__ == "__main__":
    pytest.main([__file__])
