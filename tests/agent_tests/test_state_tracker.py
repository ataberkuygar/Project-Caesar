"""
Tests for State Tracker Module
"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from agent.state_tracker import StateTracker, EnvironmentState, UserPreferences

class TestEnvironmentState:
    """Test cases for EnvironmentState dataclass"""
    
    def test_environment_state_creation_default(self):
        """Test default EnvironmentState creation"""
        state = EnvironmentState()
        
        assert state.temperature == 22.0
        assert state.music_playing is False
        assert state.current_track is None
        assert state.windows_left == "closed"
        assert state.windows_right == "closed"
        assert state.seat_position == "normal"
        assert state.location == "Yalova, Turkey"
    
    def test_environment_state_creation_custom(self):
        """Test custom EnvironmentState creation"""
        state = EnvironmentState(
            temperature=25.0,
            music_playing=True,
            current_track="Test Song",
            windows_left="open",
            seat_position="reclined"
        )
        
        assert state.temperature == 25.0
        assert state.music_playing is True
        assert state.current_track == "Test Song"
        assert state.windows_left == "open"
        assert state.seat_position == "reclined"
    
    def test_environment_state_to_dict(self):
        """Test EnvironmentState to_dict conversion"""
        state = EnvironmentState(temperature=24.0, music_playing=True)
        state_dict = state.to_dict()
        
        assert isinstance(state_dict, dict)
        assert state_dict["temperature"] == 24.0
        assert state_dict["music_playing"] is True
        assert "location" in state_dict

class TestUserPreferences:
    """Test cases for UserPreferences dataclass"""
    
    def test_user_preferences_creation_default(self):
        """Test default UserPreferences creation"""
        prefs = UserPreferences()
        
        assert prefs.preferred_temperature == 22.0
        assert prefs.preferred_music_genre is None
        assert prefs.preferred_artists == []
        assert prefs.language == "en"
        assert prefs.tts_enabled is True
    
    def test_user_preferences_creation_custom(self):
        """Test custom UserPreferences creation"""
        prefs = UserPreferences(
            preferred_temperature=25.0,
            preferred_music_genre="jazz",
            preferred_artists=["Miles Davis"],
            language="tr"
        )
        
        assert prefs.preferred_temperature == 25.0
        assert prefs.preferred_music_genre == "jazz"
        assert prefs.preferred_artists == ["Miles Davis"]
        assert prefs.language == "tr"

class TestStateTracker:
    """Test cases for StateTracker"""
    
    @pytest.fixture
    def temp_state_file(self):
        """Create temporary state file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name
        yield temp_file
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    @pytest.fixture
    def state_tracker(self, temp_state_file):
        """Create StateTracker instance with temporary state file"""
        tracker = StateTracker()
        tracker.state_file = temp_state_file
        return tracker
    
    def test_state_tracker_initialization(self, state_tracker):
        """Test StateTracker initialization"""
        assert state_tracker is not None
        assert isinstance(state_tracker.environment_state, EnvironmentState)
        assert isinstance(state_tracker.user_preferences, UserPreferences)
        assert isinstance(state_tracker.context_history, list)
        assert state_tracker.max_history_size == 100
    
    @pytest.mark.asyncio
    async def test_get_current_context(self, state_tracker):
        """Test getting current context"""
        context = await state_tracker.get_current_context()
        
        assert isinstance(context, dict)
        assert "environment" in context
        assert "preferences" in context
        assert "timestamp" in context
        assert "recent_history" in context
        assert "derived" in context
        
        # Check environment data
        assert context["environment"]["temperature"] == 22.0
        assert context["environment"]["music_playing"] is False
        
        # Check derived insights
        assert "temperature_comfort" in context["derived"]
        assert "music_status" in context["derived"]
        assert "time_period" in context["derived"]
    
    def test_derive_context_insights(self, state_tracker):
        """Test context insights derivation"""
        # Set up test state
        state_tracker.environment_state.temperature = 18.0  # Cold
        state_tracker.user_preferences.preferred_temperature = 22.0
        state_tracker.environment_state.music_playing = True
        state_tracker.environment_state.windows_left = "open"
        
        insights = state_tracker._derive_context_insights()
        
        assert insights["temperature_comfort"] == "uncomfortable"  # 4 degree difference
        assert insights["music_status"] == "playing"
        assert insights["ventilation"] == "natural"  # Window open
        assert insights["time_period"] in ["morning", "afternoon", "evening", "night"]
    
    @pytest.mark.asyncio
    async def test_update_context_temperature(self, state_tracker):
        """Test context update with temperature tool"""
        user_input = "Set temperature to 24"
        agent_response = "Temperature set to 24°C"
        tool_results = [{
            "success": True,
            "tool": "set_temperature",
            "arguments": {"temperature": 24},
            "result": {"current_temperature": 24}
        }]
        
        updated = await state_tracker.update_context(user_input, agent_response, tool_results)
        
        assert updated is True
        assert state_tracker.environment_state.temperature == 24.0
        assert len(state_tracker.context_history) == 1
    
    @pytest.mark.asyncio
    async def test_update_context_music(self, state_tracker):
        """Test context update with music tool"""
        user_input = "Play jazz music"
        agent_response = "Playing jazz music"
        tool_results = [{
            "success": True,
            "tool": "play_spotify",
            "arguments": {"track": "Blue in Green"},
            "result": {"track": "Blue in Green"}
        }]
        
        updated = await state_tracker.update_context(user_input, agent_response, tool_results)
        
        assert updated is True
        assert state_tracker.environment_state.music_playing is True
        assert state_tracker.environment_state.current_track == "Blue in Green"
    
    @pytest.mark.asyncio
    async def test_update_context_window(self, state_tracker):
        """Test context update with window tool"""
        user_input = "Open left window"
        agent_response = "Left window opened"
        tool_results = [{
            "success": True,
            "tool": "open_window",
            "arguments": {"side": "left", "action": "open"},
            "result": {"window_state": "left_open"}
        }]
        
        updated = await state_tracker.update_context(user_input, agent_response, tool_results)
        
        assert updated is True
        assert state_tracker.environment_state.windows_left == "open"
    
    @pytest.mark.asyncio
    async def test_remember_preference_temperature(self, state_tracker):
        """Test remembering temperature preference"""
        result = await state_tracker.remember_preference("preferred_temperature", 25.0)
        
        assert result is True
        assert state_tracker.user_preferences.preferred_temperature == 25.0
    
    @pytest.mark.asyncio
    async def test_remember_preference_music_genre(self, state_tracker):
        """Test remembering music genre preference"""
        result = await state_tracker.remember_preference("preferred_music_genre", "rock")
        
        assert result is True
        assert state_tracker.user_preferences.preferred_music_genre == "rock"
    
    @pytest.mark.asyncio
    async def test_remember_preference_artist(self, state_tracker):
        """Test remembering artist preference"""
        result = await state_tracker.remember_preference("preferred_artist", "The Beatles")
        
        assert result is True
        assert "The Beatles" in state_tracker.user_preferences.preferred_artists
    
    @pytest.mark.asyncio
    async def test_get_preference(self, state_tracker):
        """Test getting preferences"""
        # Set some preferences
        await state_tracker.remember_preference("preferred_temperature", 24.0)
        await state_tracker.remember_preference("preferred_music_genre", "jazz")
        
        temp_pref = await state_tracker.get_preference("preferred_temperature")
        genre_pref = await state_tracker.get_preference("preferred_music_genre")
        unknown_pref = await state_tracker.get_preference("unknown_preference")
        
        assert temp_pref == 24.0
        assert genre_pref == "jazz"
        assert unknown_pref is None
    
    @pytest.mark.asyncio
    async def test_get_context_summary(self, state_tracker):
        """Test getting context summary"""
        # Set up some state
        state_tracker.environment_state.temperature = 24.0
        state_tracker.environment_state.music_playing = True
        state_tracker.environment_state.current_track = "Test Song"
        state_tracker.environment_state.windows_left = "open"
        
        summary = await state_tracker.get_context_summary()
        
        assert isinstance(summary, str)
        assert "24" in summary  # Temperature
        assert "Test Song" in summary  # Current track
        assert "left" in summary  # Open window
    
    @pytest.mark.asyncio
    async def test_reset_context(self, state_tracker):
        """Test context reset"""
        # Modify state
        state_tracker.environment_state.temperature = 30.0
        state_tracker.user_preferences.preferred_temperature = 25.0
        state_tracker.context_history = [{"test": "data"}]
        
        await state_tracker.reset_context()
        
        assert state_tracker.environment_state.temperature == 22.0  # Default
        assert state_tracker.user_preferences.preferred_temperature == 22.0  # Default
        assert len(state_tracker.context_history) == 0
    
    @pytest.mark.asyncio
    async def test_save_conversation_history(self, state_tracker, temp_state_file):
        """Test saving conversation history"""
        conversation = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        # Mock the history file path
        history_file = temp_state_file.replace('.json', '_history.json')
        
        with patch('os.path.join', return_value=history_file):
            await state_tracker.save_conversation_history(conversation)
        
        # Check if file was created (in real scenario)
        assert True  # This test mainly checks no exceptions are thrown
    
    @pytest.mark.asyncio
    async def test_save_and_load_state(self, state_tracker, temp_state_file):
        """Test saving and loading state"""
        # Modify state
        state_tracker.environment_state.temperature = 25.0
        state_tracker.user_preferences.preferred_temperature = 24.0
        state_tracker.context_history = [{"test": "data"}]
        
        # Save state
        await state_tracker._save_state()
        
        # Verify file exists and has content
        assert os.path.exists(temp_state_file)
        
        with open(temp_state_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["environment"]["temperature"] == 25.0
        assert saved_data["preferences"]["preferred_temperature"] == 24.0
        assert len(saved_data["context_history"]) == 1
        
        # Create new tracker and load state
        new_tracker = StateTracker()
        new_tracker.state_file = temp_state_file
        await new_tracker._load_state()
        
        assert new_tracker.environment_state.temperature == 25.0
        assert new_tracker.user_preferences.preferred_temperature == 24.0
        assert len(new_tracker.context_history) == 1
    
    def test_get_state_statistics(self, state_tracker):
        """Test getting state statistics"""
        # Add some data
        state_tracker.context_history = [{"test": "data"}]
        state_tracker.user_preferences.preferred_artists = ["Artist1", "Artist2"]
        state_tracker.environment_state.music_playing = True
        
        stats = state_tracker.get_state_statistics()
        
        assert isinstance(stats, dict)
        assert stats["context_history_size"] == 1
        assert stats["preferred_artists_count"] == 2
        assert stats["current_temperature"] == 22.0  # Default
        assert stats["music_playing"] is True
        assert "state_file_exists" in stats
    
    @pytest.mark.asyncio
    async def test_context_history_trimming(self, state_tracker):
        """Test that context history is trimmed when it gets too long"""
        # Set a small max size for testing
        state_tracker.max_history_size = 3
        
        # Add more entries than max size
        for i in range(5):
            await state_tracker.update_context(
                f"Input {i}",
                f"Response {i}",
                []
            )
        
        # Should only keep the last 3 entries
        assert len(state_tracker.context_history) == 3
        assert state_tracker.context_history[0]["user_input"] == "Input 2"
        assert state_tracker.context_history[-1]["user_input"] == "Input 4"

if __name__ == "__main__":
    pytest.main([__file__])
