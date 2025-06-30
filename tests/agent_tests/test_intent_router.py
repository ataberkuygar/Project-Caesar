"""
Tests for Intent Router Module
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from agent.intent_router import IntentRouter, IntentType, IntentResult

class TestIntentRouter:
    """Test cases for IntentRouter"""
    
    @pytest.fixture
    def intent_router(self):
        """Create IntentRouter instance"""
        return IntentRouter()
    
    def test_intent_router_initialization(self, intent_router):
        """Test IntentRouter initialization"""
        assert intent_router is not None
        assert isinstance(intent_router.intent_patterns, dict)
        assert isinstance(intent_router.intent_tool_mapping, dict)
        assert len(intent_router.intent_patterns) > 0
        assert len(intent_router.intent_tool_mapping) > 0
    
    @pytest.mark.asyncio
    async def test_route_intent_temperature_control(self, intent_router):
        """Test intent routing for temperature control"""
        user_input = "It's too cold, please increase the temperature to 25 degrees"
        result = await intent_router.route_intent(user_input)
        
        assert result["intent_type"] == IntentType.TEMPERATURE_CONTROL.value
        assert result["confidence"] > 0
        assert "set_temperature" in result["suggested_tools"]
        assert result["extracted_parameters"].get("temperature") == 25.0
    
    @pytest.mark.asyncio
    async def test_route_intent_music_control(self, intent_router):
        """Test intent routing for music control"""
        user_input = "Play some jazz music please"
        result = await intent_router.route_intent(user_input)
        
        assert result["intent_type"] == IntentType.MUSIC_CONTROL.value
        assert result["confidence"] > 0
        assert any(tool in result["suggested_tools"] for tool in ["set_music", "play_spotify"])
        assert result["extracted_parameters"].get("genre") == "jazz"
    
    @pytest.mark.asyncio
    async def test_route_intent_window_control(self, intent_router):
        """Test intent routing for window control"""
        user_input = "Open the left window for some fresh air"
        result = await intent_router.route_intent(user_input)
        
        assert result["intent_type"] == IntentType.WINDOW_CONTROL.value
        assert result["confidence"] > 0
        assert "open_window" in result["suggested_tools"]
        assert result["extracted_parameters"].get("side") == "left"
        assert result["extracted_parameters"].get("action") == "open"
    
    @pytest.mark.asyncio
    async def test_route_intent_weather_inquiry(self, intent_router):
        """Test intent routing for weather inquiry"""
        user_input = "What's the weather like today?"
        result = await intent_router.route_intent(user_input)
        
        assert result["intent_type"] == IntentType.WEATHER_INQUIRY.value
        assert result["confidence"] > 0
        assert "get_weather" in result["suggested_tools"]
    
    @pytest.mark.asyncio
    async def test_route_intent_navigation(self, intent_router):
        """Test intent routing for navigation"""
        user_input = "Navigate to Istanbul please"
        result = await intent_router.route_intent(user_input)
        
        assert result["intent_type"] == IntentType.NAVIGATION.value
        assert result["confidence"] > 0
        assert any(tool in result["suggested_tools"] for tool in ["reroute", "get_location"])
        assert result["extracted_parameters"].get("destination") == "istanbul"
    
    @pytest.mark.asyncio
    async def test_route_intent_conversation(self, intent_router):
        """Test intent routing for general conversation"""
        user_input = "Hello, how are you today?"
        result = await intent_router.route_intent(user_input)
        
        assert result["intent_type"] == IntentType.CONVERSATION.value
        assert result["confidence"] > 0
        assert "talk" in result["suggested_tools"]
    
    @pytest.mark.asyncio
    async def test_route_intent_unknown(self, intent_router):
        """Test intent routing for unknown input"""
        user_input = "xyzabc123 random gibberish"
        result = await intent_router.route_intent(user_input)
        
        # Should fallback to conversation
        assert result["intent_type"] in [IntentType.CONVERSATION.value, IntentType.UNKNOWN.value]
        assert "talk" in result["suggested_tools"]
    
    def test_classify_intent_temperature(self, intent_router):
        """Test intent classification for temperature"""
        user_input = "too hot in here"
        result = intent_router._classify_intent(user_input)
        
        assert result.intent_type == IntentType.TEMPERATURE_CONTROL
        assert result.confidence > 0
        assert "set_temperature" in result.suggested_tools
    
    def test_extract_parameters_temperature(self, intent_router):
        """Test parameter extraction for temperature"""
        user_input = "set temperature to 23 degrees"
        params = intent_router._extract_parameters(user_input, IntentType.TEMPERATURE_CONTROL)
        
        assert params["temperature"] == 23.0
    
    def test_extract_parameters_temperature_direction(self, intent_router):
        """Test parameter extraction for temperature direction"""
        user_input = "it's too cold, make it warmer"
        params = intent_router._extract_parameters(user_input, IntentType.TEMPERATURE_CONTROL)
        
        assert params["direction"] == "increase"
    
    def test_extract_parameters_music(self, intent_router):
        """Test parameter extraction for music"""
        user_input = "play Hotel California by Eagles"
        params = intent_router._extract_parameters(user_input, IntentType.MUSIC_CONTROL)
        
        assert "hotel california" in params["track"].lower()
    
    def test_extract_parameters_window(self, intent_router):
        """Test parameter extraction for window control"""
        user_input = "close the right window"
        params = intent_router._extract_parameters(user_input, IntentType.WINDOW_CONTROL)
        
        assert params["side"] == "right"
        assert params["action"] == "close"
    
    def test_predict_action_temperature(self, intent_router):
        """Test action prediction for temperature"""
        user_input = "too cold"
        action = intent_router._predict_action(user_input, IntentType.TEMPERATURE_CONTROL)
        
        assert action == "increase_temperature"
    
    def test_predict_action_music(self, intent_router):
        """Test action prediction for music"""
        user_input = "play some music"
        action = intent_router._predict_action(user_input, IntentType.MUSIC_CONTROL)
        
        assert action == "play_music"
    
    def test_get_available_tools(self, intent_router):
        """Test getting available tools"""
        tools = intent_router._get_available_tools(IntentType.TEMPERATURE_CONTROL)
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert any(tool["name"] == "set_temperature" for tool in tools)
    
    def test_get_intent_statistics(self, intent_router):
        """Test getting intent statistics"""
        stats = intent_router.get_intent_statistics()
        
        assert "supported_intents" in stats
        assert "total_patterns" in stats
        assert "tool_mappings" in stats
        assert isinstance(stats["supported_intents"], list)
        assert isinstance(stats["total_patterns"], int)
        assert stats["total_patterns"] > 0

class TestIntentResult:
    """Test cases for IntentResult dataclass"""
    
    def test_intent_result_creation(self):
        """Test IntentResult creation"""
        result = IntentResult(
            intent_type=IntentType.TEMPERATURE_CONTROL,
            confidence=0.8,
            suggested_tools=["set_temperature"],
            extracted_parameters={"temperature": 22},
            predicted_action="adjust_temperature"
        )
        
        assert result.intent_type == IntentType.TEMPERATURE_CONTROL
        assert result.confidence == 0.8
        assert result.suggested_tools == ["set_temperature"]
        assert result.extracted_parameters["temperature"] == 22
        assert result.predicted_action == "adjust_temperature"

if __name__ == "__main__":
    pytest.main([__file__])
