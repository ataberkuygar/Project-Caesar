"""
Dialogue Handler Module
Handles conversations and Text-to-Speech functionality
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import os

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

class DialogueHandler:
    """
    Handles dialogue management including:
    - Text-to-Speech conversion
    - Response formatting
    - Conversation flow management
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # TTS Configuration
        self.tts_enabled = os.getenv("TTS_ENGINE", "pyttsx3") == "pyttsx3"
        self.voice_rate = int(os.getenv("TTS_VOICE_RATE", 200))
        self.voice_volume = float(os.getenv("TTS_VOICE_VOLUME", 0.8))
        
        # Initialize TTS engine
        self.tts_engine = None
        if self.tts_enabled and pyttsx3:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', self.voice_rate)
                self.tts_engine.setProperty('volume', self.voice_volume)
                self.logger.info("TTS engine initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize TTS engine: {str(e)}")
                self.tts_engine = None
        
        # Greeting messages
        self.greetings = [
            "Hello! I'm your AI assistant for this journey through Yalova. How can I help you today?",
            "Welcome to your smart car experience! I'm here to assist with temperature, music, and more.",
            "Good to see you! Ready for a comfortable drive through rural Yalova?",
            "Hi there! I can help control your car's settings and provide information during our trip."
        ]
        
        self.logger.info("Dialogue Handler initialized")
    
    async def handle_response(self, agent_response) -> None:
        """
        Handle agent response including TTS and formatting
        """
        try:
            message = agent_response.message
            
            # Format response for display
            formatted_message = self._format_response(message, agent_response)
            
            # Log the response
            self.logger.info(f"Agent response: {formatted_message}")
            
            # Speak the response if TTS is enabled
            if self.tts_enabled:
                await self._speak_async(message)
            
            # Additional processing based on action taken
            if agent_response.action_taken:
                await self._handle_action_feedback(agent_response.action_taken)
                
        except Exception as e:
            self.logger.error(f"Error handling response: {str(e)}")
    
    def _format_response(self, message: str, agent_response) -> str:
        """Format response message for display"""
        formatted = message
        
        # Add action indicators
        if agent_response.tool_calls:
            successful_actions = [call for call in agent_response.tool_calls if call.get("success", False)]
            if successful_actions:
                actions = ", ".join([call["tool"] for call in successful_actions])
                formatted += f" [Actions: {actions}]"
        
        # Add timestamp
        timestamp = agent_response.timestamp.strftime("%H:%M:%S")
        formatted += f" ({timestamp})"
        
        return formatted
    
    async def _speak_async(self, text: str) -> None:
        """Speak text asynchronously using TTS"""
        if not self.tts_engine:
            return
        
        try:
            # Run TTS in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._speak_sync, text)
        except Exception as e:
            self.logger.error(f"TTS error: {str(e)}")
    
    def _speak_sync(self, text: str) -> None:
        """Synchronous TTS function"""
        if self.tts_engine:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
    
    async def speak(self, text: str) -> None:
        """Public method to speak text"""
        await self._speak_async(text)
    
    async def _handle_action_feedback(self, action: str) -> None:
        """Provide audio feedback for specific actions"""
        feedback_sounds = {
            "increase_temperature": "Temperature increased",
            "decrease_temperature": "Temperature decreased", 
            "play_music": "Music started",
            "stop_music": "Music stopped",
            "open_window": "Window opened",
            "close_window": "Window closed"
        }
        
        if action in feedback_sounds and self.tts_enabled:
            # Small delay before feedback
            await asyncio.sleep(0.5)
            # Could add sound effects here in the future
    
    async def get_greeting(self) -> str:
        """Get a random greeting message"""
        import random
        return random.choice(self.greetings)
    
    def set_voice_properties(self, rate: Optional[int] = None, volume: Optional[float] = None) -> bool:
        """Update TTS voice properties"""
        if not self.tts_engine:
            return False
        
        try:
            if rate is not None:
                self.tts_engine.setProperty('rate', rate)
                self.voice_rate = rate
            
            if volume is not None:
                self.tts_engine.setProperty('volume', volume)
                self.voice_volume = volume
            
            return True
        except Exception as e:
            self.logger.error(f"Error setting voice properties: {str(e)}")
            return False
    
    def get_available_voices(self) -> list:
        """Get list of available TTS voices"""
        if not self.tts_engine:
            return []
        
        try:
            voices = self.tts_engine.getProperty('voices')
            return [{"id": voice.id, "name": voice.name} for voice in voices] if voices else []
        except Exception as e:
            self.logger.error(f"Error getting voices: {str(e)}")
            return []
    
    def set_voice(self, voice_id: str) -> bool:
        """Set TTS voice by ID"""
        if not self.tts_engine:
            return False
        
        try:
            self.tts_engine.setProperty('voice', voice_id)
            return True
        except Exception as e:
            self.logger.error(f"Error setting voice: {str(e)}")
            return False
    
    async def handle_user_input_feedback(self, user_input: str) -> None:
        """Provide feedback when receiving user input"""
        # Could add input acknowledgment sounds/animations
        pass
    
    def format_conversation_history(self, history: list) -> str:
        """Format conversation history for display"""
        formatted_lines = []
        
        for entry in history:
            timestamp = entry.get("timestamp", "")
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            
            if timestamp:
                time_str = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime("%H:%M")
                formatted_lines.append(f"[{time_str}] {role.capitalize()}: {content}")
            else:
                formatted_lines.append(f"{role.capitalize()}: {content}")
        
        return "\n".join(formatted_lines)
    
    async def close(self):
        """Clean up resources"""
        if self.tts_engine:
            try:
                self.tts_engine.stop()
            except Exception as e:
                self.logger.warning(f"Error stopping TTS engine: {e}")
                pass
        self.logger.info("Dialogue Handler closed")
