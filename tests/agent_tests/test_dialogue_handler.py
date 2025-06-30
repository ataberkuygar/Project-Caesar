"""
Tests for Dialogue Handler Module  
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Mock external dependencies
sys.modules['pyttsx3'] = Mock()

from agent.dialogue_handler import DialogueHandler
from agent.agent_core import AgentResponse

class TestDialogueHandler:
    """Test cases for DialogueHandler"""
    
    @pytest.fixture
    def mock_tts_engine(self):
        """Mock TTS engine"""
        mock_engine = Mock()
        mock_engine.setProperty = Mock()
        mock_engine.say = Mock()
        mock_engine.runAndWait = Mock()
        mock_engine.stop = Mock()
        mock_engine.getProperty.return_value = []
        return mock_engine
    
    @pytest.fixture
    def dialogue_handler(self, mock_tts_engine):
        """Create DialogueHandler instance with mocked TTS"""
        with patch.dict(os.environ, {
            'TTS_ENGINE': 'pyttsx3',
            'TTS_VOICE_RATE': '200',
            'TTS_VOICE_VOLUME': '0.8'
        }):
            with patch('agent.dialogue_handler.pyttsx3') as mock_pyttsx3:
                mock_pyttsx3.init.return_value = mock_tts_engine
                handler = DialogueHandler()
                return handler
    
    def test_dialogue_handler_initialization(self, dialogue_handler):
        """Test DialogueHandler initialization"""
        assert dialogue_handler is not None
        assert dialogue_handler.tts_enabled is True
        assert dialogue_handler.voice_rate == 200
        assert dialogue_handler.voice_volume == 0.8
        assert len(dialogue_handler.greetings) > 0
    
    def test_dialogue_handler_initialization_no_tts(self):
        """Test DialogueHandler initialization without TTS"""
        with patch.dict(os.environ, {'TTS_ENGINE': 'none'}):
            with patch('agent.dialogue_handler.pyttsx3', None):
                handler = DialogueHandler()
                assert handler.tts_enabled is False
                assert handler.tts_engine is None
    
    @pytest.mark.asyncio
    async def test_handle_response_basic(self, dialogue_handler):
        """Test basic response handling"""
        response = AgentResponse(
            message="Test response",
            action_taken="test_action"
        )
        
        dialogue_handler._speak_async = AsyncMock()
        dialogue_handler._handle_action_feedback = AsyncMock()
        
        await dialogue_handler.handle_response(response)
        
        dialogue_handler._speak_async.assert_called_once_with("Test response")
        dialogue_handler._handle_action_feedback.assert_called_once_with("test_action")
    
    @pytest.mark.asyncio
    async def test_handle_response_with_tool_calls(self, dialogue_handler):
        """Test response handling with tool calls"""
        tool_calls = [
            {"tool": "set_temperature", "success": True},
            {"tool": "play_music", "success": True}
        ]
        response = AgentResponse(
            message="Done",
            tool_calls=tool_calls
        )
        
        dialogue_handler._speak_async = AsyncMock()
        
        await dialogue_handler.handle_response(response)
        
        dialogue_handler._speak_async.assert_called_once_with("Done")
    
    def test_format_response_basic(self, dialogue_handler):
        """Test basic response formatting"""
        response = AgentResponse(message="Test message")
        
        formatted = dialogue_handler._format_response("Test message", response)
        
        assert "Test message" in formatted
        assert response.timestamp.strftime("%H:%M:%S") in formatted
    
    def test_format_response_with_actions(self, dialogue_handler):
        """Test response formatting with actions"""
        tool_calls = [
            {"tool": "set_temperature", "success": True},
            {"tool": "play_music", "success": True}
        ]
        response = AgentResponse(
            message="Test message",
            tool_calls=tool_calls
        )
        
        formatted = dialogue_handler._format_response("Test message", response)
        
        assert "Test message" in formatted
        assert "[Actions:" in formatted
        assert "set_temperature" in formatted
        assert "play_music" in formatted
    
    @pytest.mark.asyncio
    async def test_speak_async(self, dialogue_handler, mock_tts_engine):
        """Test asynchronous speaking"""
        text = "Hello world"
        
        await dialogue_handler._speak_async(text)
        
        # TTS should be called in executor, so we just verify no exceptions
        assert True  # If we get here, no exceptions were thrown
    
    def test_speak_sync(self, dialogue_handler, mock_tts_engine):
        """Test synchronous speaking"""
        text = "Hello world"
        
        dialogue_handler._speak_sync(text)
        
        mock_tts_engine.say.assert_called_once_with(text)
        mock_tts_engine.runAndWait.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_speak_public_method(self, dialogue_handler):
        """Test public speak method"""
        dialogue_handler._speak_async = AsyncMock()
        
        await dialogue_handler.speak("Test message")
        
        dialogue_handler._speak_async.assert_called_once_with("Test message")
    
    @pytest.mark.asyncio
    async def test_handle_action_feedback(self, dialogue_handler):
        """Test action feedback handling"""
        dialogue_handler._speak_async = AsyncMock()
        
        # Test with feedback action
        await dialogue_handler._handle_action_feedback("increase_temperature")
        
        # Should complete without error
        assert True
    
    @pytest.mark.asyncio
    async def test_get_greeting(self, dialogue_handler):
        """Test getting greeting message"""
        greeting = await dialogue_handler.get_greeting()
        
        assert isinstance(greeting, str)
        assert len(greeting) > 0
        assert greeting in dialogue_handler.greetings
    
    def test_set_voice_properties_success(self, dialogue_handler, mock_tts_engine):
        """Test setting voice properties successfully"""
        result = dialogue_handler.set_voice_properties(rate=180, volume=0.9)
        
        assert result is True
        mock_tts_engine.setProperty.assert_any_call('rate', 180)
        mock_tts_engine.setProperty.assert_any_call('volume', 0.9)
        assert dialogue_handler.voice_rate == 180
        assert dialogue_handler.voice_volume == 0.9
    
    def test_set_voice_properties_no_engine(self, dialogue_handler):
        """Test setting voice properties without TTS engine"""
        dialogue_handler.tts_engine = None
        
        result = dialogue_handler.set_voice_properties(rate=180)
        
        assert result is False
    
    def test_set_voice_properties_partial(self, dialogue_handler, mock_tts_engine):
        """Test setting voice properties partially"""
        original_volume = dialogue_handler.voice_volume
        
        result = dialogue_handler.set_voice_properties(rate=150)
        
        assert result is True
        mock_tts_engine.setProperty.assert_called_with('rate', 150)
        assert dialogue_handler.voice_rate == 150
        assert dialogue_handler.voice_volume == original_volume  # Unchanged
    
    def test_get_available_voices(self, dialogue_handler, mock_tts_engine):
        """Test getting available voices"""
        # Mock voice objects
        mock_voice1 = Mock()
        mock_voice1.id = "voice1"
        mock_voice1.name = "Voice 1"
        mock_voice2 = Mock()
        mock_voice2.id = "voice2"
        mock_voice2.name = "Voice 2"
        
        mock_tts_engine.getProperty.return_value = [mock_voice1, mock_voice2]
        
        voices = dialogue_handler.get_available_voices()
        
        assert isinstance(voices, list)
        assert len(voices) == 2
        assert voices[0]["id"] == "voice1"
        assert voices[0]["name"] == "Voice 1"
        assert voices[1]["id"] == "voice2"
        assert voices[1]["name"] == "Voice 2"
    
    def test_get_available_voices_no_engine(self, dialogue_handler):
        """Test getting voices without TTS engine"""
        dialogue_handler.tts_engine = None
        
        voices = dialogue_handler.get_available_voices()
        
        assert isinstance(voices, list)
        assert len(voices) == 0
    
    def test_set_voice_success(self, dialogue_handler, mock_tts_engine):
        """Test setting voice successfully"""
        voice_id = "test_voice_id"
        
        result = dialogue_handler.set_voice(voice_id)
        
        assert result is True
        mock_tts_engine.setProperty.assert_called_with('voice', voice_id)
    
    def test_set_voice_no_engine(self, dialogue_handler):
        """Test setting voice without TTS engine"""
        dialogue_handler.tts_engine = None
        
        result = dialogue_handler.set_voice("test_voice")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_handle_user_input_feedback(self, dialogue_handler):
        """Test user input feedback handling"""
        # Should complete without error
        await dialogue_handler.handle_user_input_feedback("Test input")
        assert True
    
    def test_format_conversation_history(self, dialogue_handler):
        """Test conversation history formatting"""
        history = [
            {
                "timestamp": "2024-01-01T12:00:00",
                "role": "user",
                "content": "Hello"
            },
            {
                "timestamp": "2024-01-01T12:00:01",
                "role": "assistant", 
                "content": "Hi there!"
            },
            {
                "role": "user",
                "content": "How are you?"
            }
        ]
        
        formatted = dialogue_handler.format_conversation_history(history)
        
        assert isinstance(formatted, str)
        assert "User: Hello" in formatted
        assert "Assistant: Hi there!" in formatted
        assert "User: How are you?" in formatted
        assert "[12:00]" in formatted  # Time should be formatted
    
    def test_format_conversation_history_empty(self, dialogue_handler):
        """Test formatting empty conversation history"""
        history = []
        
        formatted = dialogue_handler.format_conversation_history(history)
        
        assert formatted == ""
    
    @pytest.mark.asyncio
    async def test_close(self, dialogue_handler, mock_tts_engine):
        """Test closing dialogue handler"""
        await dialogue_handler.close()
        
        mock_tts_engine.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_no_engine(self, dialogue_handler):
        """Test closing without TTS engine"""
        dialogue_handler.tts_engine = None
        
        # Should complete without error
        await dialogue_handler.close()
        assert True
    
    @pytest.mark.asyncio
    async def test_handle_response_exception_handling(self, dialogue_handler):
        """Test response handling with exceptions"""
        response = AgentResponse(message="Test")
        
        # Mock an exception in formatting
        dialogue_handler._format_response = Mock(side_effect=Exception("Test error"))
        
        # Should handle exception gracefully
        await dialogue_handler.handle_response(response)
        assert True  # No exception should propagate
    
    def test_tts_engine_initialization_failure(self, mock_tts_engine):
        """Test TTS engine initialization failure"""
        with patch.dict(os.environ, {'TTS_ENGINE': 'pyttsx3'}):
            with patch('agent.dialogue_handler.pyttsx3') as mock_pyttsx3:
                mock_pyttsx3.init.side_effect = Exception("TTS init failed")
                
                handler = DialogueHandler()
                
                assert handler.tts_engine is None

if __name__ == "__main__":
    pytest.main([__file__])
