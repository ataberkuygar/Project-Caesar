"""
State Tracker Module
Stores current environment state and context
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import os

@dataclass
class EnvironmentState:
    """Current state of the car and environment"""
    temperature: float = 22.0
    music_playing: bool = False
    current_track: Optional[str] = None
    windows_left: str = "closed"  # "open", "closed", "partial"
    windows_right: str = "closed"
    seat_position: str = "normal"
    location: str = "Yalova, Turkey"
    latitude: float = 40.6553
    longitude: float = 29.2769
    speed: float = 0.0
    weather_condition: str = "unknown"
    weather_temperature: float = 18.0
    time_of_day: str = "day"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

@dataclass
class UserPreferences:
    """User preferences and memory"""
    preferred_temperature: float = 22.0
    preferred_music_genre: Optional[str] = None
    preferred_artists: List[str] = None
    language: str = "en"
    tts_enabled: bool = True
    voice_rate: int = 200
    
    def __post_init__(self):
        if self.preferred_artists is None:
            self.preferred_artists = []

class StateTracker:
    """
    Tracks and manages current environment state and user context
    Provides persistence and context management for the AI agent
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Current state
        self.environment_state = EnvironmentState()
        self.user_preferences = UserPreferences()
        
        # Context history
        self.context_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
        
        # State file for persistence
        self.state_file = os.path.join(os.getcwd(), "agent_state.json")
        
        # Load saved state if available (sync version for init)
        self._load_state_sync()
        
        self.logger.info("State Tracker initialized")
    
    async def get_current_context(self) -> Dict[str, Any]:
        """Get current complete context"""
        try:
            context = {
                "environment": self.environment_state.to_dict(),
                "preferences": asdict(self.user_preferences),
                "timestamp": datetime.utcnow().isoformat(),
                "recent_history": self.context_history[-10:] if self.context_history else []
            }
            
            # Add derived context
            context["derived"] = self._derive_context_insights()
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error getting current context: {str(e)}")
            return self._get_default_context()
    
    def _derive_context_insights(self) -> Dict[str, Any]:
        """Derive insights from current state"""
        insights = {}
        
        # Temperature comfort level
        temp_diff = abs(self.environment_state.temperature - self.user_preferences.preferred_temperature)
        if temp_diff > 3:
            insights["temperature_comfort"] = "uncomfortable"
        elif temp_diff > 1:
            insights["temperature_comfort"] = "slightly_uncomfortable"
        else:
            insights["temperature_comfort"] = "comfortable"
        
        # Music status
        insights["music_status"] = "playing" if self.environment_state.music_playing else "stopped"
        
        # Window status
        windows_open = (self.environment_state.windows_left == "open" or 
                       self.environment_state.windows_right == "open")
        insights["ventilation"] = "natural" if windows_open else "climate_controlled"
        
        # Time context
        current_hour = datetime.now().hour
        if 6 <= current_hour < 12:
            insights["time_period"] = "morning"
        elif 12 <= current_hour < 18:
            insights["time_period"] = "afternoon"
        elif 18 <= current_hour < 22:
            insights["time_period"] = "evening"
        else:
            insights["time_period"] = "night"
        
        return insights
    
    async def update_context(self, user_input: str, agent_response: str, 
                           tool_results: List[Dict[str, Any]]) -> bool:
        """Update context based on interaction"""
        try:
            # Process tool results to update environment state
            state_updated = False
            
            for result in tool_results:
                if result.get("success"):
                    tool_name = result.get("tool")
                    args = result.get("arguments", {})
                    
                    state_updated |= await self._update_state_from_tool(tool_name, args, result.get("result", {}))
            
            # Add to context history
            context_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "agent_response": agent_response,
                "tool_results": tool_results,
                "state_snapshot": self.environment_state.to_dict()
            }
            
            self.context_history.append(context_entry)
            
            # Trim history if too long
            if len(self.context_history) > self.max_history_size:
                self.context_history = self.context_history[-self.max_history_size:]
            
            # Save state periodically
            if state_updated:
                await self._save_state()
            
            return state_updated
            
        except Exception as e:
            self.logger.error(f"Error updating context: {str(e)}")
            return False
    
    async def _update_state_from_tool(self, tool_name: str, args: Dict[str, Any], 
                                    result: Dict[str, Any]) -> bool:
        """Update environment state based on tool execution"""
        state_updated = False
        
        try:
            if tool_name == "set_temperature":
                new_temp = args.get("temperature") or result.get("current_temperature")
                if new_temp:
                    self.environment_state.temperature = float(new_temp)
                    state_updated = True
            
            elif tool_name == "set_music" or tool_name == "play_spotify":
                track = args.get("track") or result.get("track")
                if track:
                    self.environment_state.current_track = track
                    self.environment_state.music_playing = True
                    state_updated = True
            
            elif tool_name == "open_window":
                side = args.get("side", "both")
                action = args.get("action", "open")
                
                if side in ["left", "both"]:
                    self.environment_state.windows_left = action
                if side in ["right", "both"]:
                    self.environment_state.windows_right = action
                state_updated = True
            
            elif tool_name == "adjust_seat":
                position = args.get("position")
                if position:
                    self.environment_state.seat_position = position
                    state_updated = True
            
            elif tool_name == "get_weather":
                if result.get("temperature"):
                    self.environment_state.weather_temperature = result["temperature"]
                if result.get("condition"):
                    self.environment_state.weather_condition = result["condition"]
                state_updated = True
            
            elif tool_name == "get_location":
                if result.get("latitude"):
                    self.environment_state.latitude = result["latitude"]
                if result.get("longitude"):
                    self.environment_state.longitude = result["longitude"]
                if result.get("location"):
                    self.environment_state.location = result["location"]
                state_updated = True
        
        except Exception as e:
            self.logger.error(f"Error updating state from tool {tool_name}: {str(e)}")
        
        return state_updated
    
    async def remember_preference(self, key: str, value: Any) -> bool:
        """Store user preference"""
        try:
            if key == "preferred_temperature":
                self.user_preferences.preferred_temperature = float(value)
            elif key == "preferred_music_genre":
                self.user_preferences.preferred_music_genre = str(value)
            elif key == "preferred_artist":
                if value not in self.user_preferences.preferred_artists:
                    self.user_preferences.preferred_artists.append(str(value))
            elif key == "language":
                self.user_preferences.language = str(value)
            elif key == "tts_enabled":
                self.user_preferences.tts_enabled = bool(value)
            else:
                # Store as custom preference in context history
                self.context_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "preference",
                    "key": key,
                    "value": value
                })
            
            await self._save_state()
            self.logger.info(f"Preference stored: {key} = {value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing preference {key}: {str(e)}")
            return False
    
    async def get_preference(self, key: str) -> Any:
        """Retrieve user preference"""
        try:
            if key == "preferred_temperature":
                return self.user_preferences.preferred_temperature
            elif key == "preferred_music_genre":
                return self.user_preferences.preferred_music_genre
            elif key == "preferred_artists":
                return self.user_preferences.preferred_artists
            elif key == "language":
                return self.user_preferences.language
            elif key == "tts_enabled":
                return self.user_preferences.tts_enabled
            else:
                # Search in context history
                for entry in reversed(self.context_history):
                    if (entry.get("type") == "preference" and 
                        entry.get("key") == key):
                        return entry.get("value")
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving preference {key}: {str(e)}")
            return None
    
    async def get_context_summary(self) -> str:
        """Get a summary of recent context"""
        try:
            recent_entries = self.context_history[-5:] if self.context_history else []
            
            summary_parts = []
            
            # Current state summary
            state = self.environment_state
            summary_parts.append(f"Temperature: {state.temperature}°C")
            
            if state.music_playing and state.current_track:
                summary_parts.append(f"Playing: {state.current_track}")
            
            windows = []
            if state.windows_left == "open":
                windows.append("left")
            if state.windows_right == "open":
                windows.append("right")
            if windows:
                summary_parts.append(f"Windows open: {', '.join(windows)}")
            
            # Recent actions
            if recent_entries:
                recent_tools = []
                for entry in recent_entries:
                    for result in entry.get("tool_results", []):
                        if result.get("success"):
                            recent_tools.append(result.get("tool", "unknown"))
                
                if recent_tools:
                    summary_parts.append(f"Recent actions: {', '.join(set(recent_tools))}")
            
            return "; ".join(summary_parts)
            
        except Exception as e:
            self.logger.error(f"Error generating context summary: {str(e)}")
            return "Context summary unavailable"
    
    async def reset_context(self) -> None:
        """Reset context to default state"""
        try:
            self.environment_state = EnvironmentState()
            self.user_preferences = UserPreferences()
            self.context_history = []
            
            await self._save_state()
            self.logger.info("Context reset to default state")
            
        except Exception as e:
            self.logger.error(f"Error resetting context: {str(e)}")
    
    async def save_conversation_history(self, conversation: List[Dict[str, Any]]) -> None:
        """Save conversation history"""
        try:
            history_file = os.path.join(os.getcwd(), "conversation_history.json")
            
            history_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "conversation": conversation,
                "final_state": self.environment_state.to_dict(),
                "preferences": asdict(self.user_preferences)
            }
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Conversation history saved to {history_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving conversation history: {str(e)}")
    
    async def _save_state(self) -> None:
        """Save current state to file"""
        try:
            state_data = {
                "environment": self.environment_state.to_dict(),
                "preferences": asdict(self.user_preferences),
                "context_history": self.context_history[-50:],  # Save last 50 entries
                "saved_at": datetime.utcnow().isoformat()
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")
    
    async def _load_state(self) -> None:
        """Load state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
                # Load environment state
                if "environment" in state_data:
                    env_data = state_data["environment"]
                    self.environment_state = EnvironmentState(**env_data)
                
                # Load preferences
                if "preferences" in state_data:
                    pref_data = state_data["preferences"]
                    self.user_preferences = UserPreferences(**pref_data)
                
                # Load context history
                if "context_history" in state_data:
                    self.context_history = state_data["context_history"]
                
                self.logger.info("State loaded from file")
            
        except Exception as e:
            self.logger.error(f"Error loading state: {str(e)}")
    
    def _load_state_sync(self) -> None:
        """Load state from file synchronously (for initialization)"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
                # Load environment state
                if "environment" in state_data:
                    env_data = state_data["environment"]
                    self.environment_state = EnvironmentState(**env_data)
                
                # Load preferences
                if "preferences" in state_data:
                    pref_data = state_data["preferences"]
                    self.user_preferences = UserPreferences(**pref_data)
                
                # Load context history
                if "context_history" in state_data:
                    self.context_history = state_data["context_history"]
                
                self.logger.info("State loaded from file")
            
        except Exception as e:
            self.logger.error(f"Error loading state: {str(e)}")
    
    def _get_default_context(self) -> Dict[str, Any]:
        """Get default context when errors occur"""
        return {
            "environment": {
                "temperature": 22.0,
                "music_playing": False,
                "location": "Yalova, Turkey",
                "windows": "closed"
            },
            "preferences": {
                "preferred_temperature": 22.0,
                "language": "en"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "recent_history": [],
            "derived": {
                "temperature_comfort": "comfortable",
                "music_status": "stopped",
                "time_period": "day"
            }
        }
    
    def get_state_statistics(self) -> Dict[str, Any]:
        """Get statistics about state tracking"""
        return {
            "context_history_size": len(self.context_history),
            "preferred_artists_count": len(self.user_preferences.preferred_artists),
            "current_temperature": self.environment_state.temperature,
            "music_playing": self.environment_state.music_playing,
            "state_file_exists": os.path.exists(self.state_file)
        }
