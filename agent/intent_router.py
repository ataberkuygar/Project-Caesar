"""
Intent Router Module
Classifies user input and routes to appropriate tools
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class IntentType(Enum):
    """Types of user intents"""
    TEMPERATURE_CONTROL = "temperature_control"
    MUSIC_CONTROL = "music_control"
    WINDOW_CONTROL = "window_control"
    SEAT_ADJUSTMENT = "seat_adjustment"
    WEATHER_INQUIRY = "weather_inquiry"
    LOCATION_REQUEST = "location_request"
    NAVIGATION = "navigation"
    CONVERSATION = "conversation"
    SIMULATION_CONTROL = "simulation_control"
    UNKNOWN = "unknown"

@dataclass
class IntentResult:
    """Result of intent classification"""
    intent_type: IntentType
    confidence: float
    suggested_tools: List[str]
    extracted_parameters: Dict[str, Any]
    predicted_action: str

class IntentRouter:
    """
    Routes user input to appropriate tools based on intent classification
    Uses pattern matching and keyword analysis for intent detection
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Intent patterns for classification
        self.intent_patterns = {
            IntentType.TEMPERATURE_CONTROL: [
                r'(cold|hot|warm|cool|temperature|degrees?|heat|ac|air conditioning)',
                r'(turn up|turn down|increase|decrease|adjust).*temperature',
                r'(too hot|too cold|freezing|boiling)',
                r'(warmer|cooler|hotter|colder)'
            ],
            IntentType.MUSIC_CONTROL: [
                r'(play|stop|pause|music|song|track|album|artist)',
                r'(turn on|turn off|start|next|previous).*music',
                r'(spotify|sound|audio|volume)',
                r'(listen to|hear|put on).*music'
            ],
            IntentType.WINDOW_CONTROL: [
                r'(window|windows|open|close|roll up|roll down)',
                r'(fresh air|ventilation|breeze)',
                r'(stuffy|air flow)'
            ],
            IntentType.SEAT_ADJUSTMENT: [
                r'(seat|chair|position|comfortable|adjust)',
                r'(forward|back|up|down|recline)',
                r'(uncomfortable|sore|posture)'
            ],
            IntentType.WEATHER_INQUIRY: [
                r'(weather|forecast|rain|sunny|cloudy|temperature outside)',
                r'(what.*like outside|how.*weather)',
                r'(will it rain|is it sunny|temperature)'
            ],
            IntentType.LOCATION_REQUEST: [
                r'(where are we|location|position|gps)',
                r'(what.*place|which.*area|current location)'
            ],
            IntentType.NAVIGATION: [
                r'(directions?|navigate|route|way to|go to|destination)',
                r'(how to get|find.*way|drive to)',
                r'(reroute|alternative|shortcut)'
            ],
            IntentType.SIMULATION_CONTROL: [
                r'(start|stop|pause|reset|restart).*simulation',
                r'(begin|end|exit).*session',
                r'(save|load).*state'
            ],
            IntentType.CONVERSATION: [
                r'(hello|hi|hey|good morning|good evening)',
                r'(how are you|thanks|thank you|please)',
                r'(tell me|explain|what|why|when|where|how)'
            ]
        }
        
        # Tool mappings for each intent
        self.intent_tool_mapping = {
            IntentType.TEMPERATURE_CONTROL: ["set_temperature"],
            IntentType.MUSIC_CONTROL: ["set_music", "play_spotify"],
            IntentType.WINDOW_CONTROL: ["open_window"],
            IntentType.SEAT_ADJUSTMENT: ["adjust_seat"],
            IntentType.WEATHER_INQUIRY: ["get_weather"],
            IntentType.LOCATION_REQUEST: ["get_location"],
            IntentType.NAVIGATION: ["reroute", "get_location"],
            IntentType.SIMULATION_CONTROL: ["start_simulation", "pause_simulation", "reset_simulation", "log_event"],
            IntentType.CONVERSATION: ["talk", "remember", "ask_confirm", "summarize"],
            IntentType.UNKNOWN: ["talk"]
        }
        
        self.logger.info("Intent Router initialized")
    
    async def route_intent(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Route user input to appropriate tools based on intent classification
        """
        try:
            # Classify intent
            intent_result = self._classify_intent(user_input)
            
            # Extract parameters based on intent
            parameters = self._extract_parameters(user_input, intent_result.intent_type)
            
            # Get available tools for this intent
            available_tools = self._get_available_tools(intent_result.intent_type)
            
            # Consider context for better routing
            if context:
                available_tools = self._refine_tools_with_context(available_tools, context)
            
            result = {
                "intent_type": intent_result.intent_type.value,
                "confidence": intent_result.confidence,
                "suggested_tools": intent_result.suggested_tools,
                "available_tools": available_tools,
                "extracted_parameters": parameters,
                "predicted_action": intent_result.predicted_action
            }
            
            self.logger.info(f"Intent routed: {intent_result.intent_type.value} (confidence: {intent_result.confidence:.2f})")
            return result
            
        except Exception as e:
            self.logger.error(f"Error routing intent: {str(e)}")
            return {
                "intent_type": IntentType.UNKNOWN.value,
                "confidence": 0.0,
                "suggested_tools": ["talk"],
                "available_tools": self._get_fallback_tools(),
                "extracted_parameters": {},
                "predicted_action": "conversation"
            }
    
    def _classify_intent(self, user_input: str) -> IntentResult:
        """Classify user intent using pattern matching"""
        user_input_lower = user_input.lower()
        intent_scores = {}
        
        # Score each intent type
        for intent_type, patterns in self.intent_patterns.items():
            score = 0
            matches = 0
            
            for pattern in patterns:
                if re.search(pattern, user_input_lower):
                    matches += 1
                    score += 1
            
            # Normalize score
            if matches > 0:
                intent_scores[intent_type] = score / len(patterns)
        
        # Find best match
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = intent_scores[best_intent]
        else:
            best_intent = IntentType.CONVERSATION
            confidence = 0.1  # Low confidence fallback
        
        # Get suggested tools
        suggested_tools = self.intent_tool_mapping.get(best_intent, ["talk"])
        
        # Predict specific action
        predicted_action = self._predict_action(user_input, best_intent)
        
        return IntentResult(
            intent_type=best_intent,
            confidence=confidence,
            suggested_tools=suggested_tools,
            extracted_parameters={},
            predicted_action=predicted_action
        )
    
    def _extract_parameters(self, user_input: str, intent_type: IntentType) -> Dict[str, Any]:
        """Extract parameters from user input based on intent type"""
        parameters = {}
        user_input_lower = user_input.lower()
        
        if intent_type == IntentType.TEMPERATURE_CONTROL:
            # Extract temperature values
            temp_match = re.search(r'(\d+)[\s]*(?:degrees?|°)', user_input_lower)
            if temp_match:
                parameters["temperature"] = float(temp_match.group(1))
            elif any(word in user_input_lower for word in ["cold", "cool", "cooler"]):
                parameters["direction"] = "decrease"
            elif any(word in user_input_lower for word in ["hot", "warm", "warmer"]):
                parameters["direction"] = "increase"
        
        elif intent_type == IntentType.MUSIC_CONTROL:
            # Extract music preferences
            if "play" in user_input_lower:
                # Try to extract song/artist name
                play_match = re.search(r'play\s+(.*?)(?:\s+by\s+|\s*$)', user_input_lower)
                if play_match:
                    parameters["track"] = play_match.group(1).strip()
            
            # Extract genre preferences
            genres = ["rock", "pop", "jazz", "classical", "electronic", "folk", "country"]
            for genre in genres:
                if genre in user_input_lower:
                    parameters["genre"] = genre
                    break
        
        elif intent_type == IntentType.WINDOW_CONTROL:
            # Extract window side
            if "left" in user_input_lower:
                parameters["side"] = "left"
            elif "right" in user_input_lower:
                parameters["side"] = "right"
            else:
                parameters["side"] = "both"
            
            # Extract action
            if any(word in user_input_lower for word in ["open", "down", "fresh air"]):
                parameters["action"] = "open"
            elif any(word in user_input_lower for word in ["close", "up"]):
                parameters["action"] = "close"
        
        elif intent_type == IntentType.SEAT_ADJUSTMENT:
            # Extract seat adjustments
            if "forward" in user_input_lower:
                parameters["position"] = "forward"
            elif "back" in user_input_lower:
                parameters["position"] = "back"
            elif "recline" in user_input_lower:
                parameters["position"] = "reclined"
            elif "up" in user_input_lower:
                parameters["position"] = "up"
        
        elif intent_type == IntentType.NAVIGATION:
            # Extract destination
            to_match = re.search(r'(?:to|go to|navigate to|directions to)\s+(.+)', user_input_lower)
            if to_match:
                parameters["destination"] = to_match.group(1).strip()
        
        return parameters
    
    def _predict_action(self, user_input: str, intent_type: IntentType) -> str:
        """Predict the specific action to take"""
        user_input_lower = user_input.lower()
        
        if intent_type == IntentType.TEMPERATURE_CONTROL:
            if any(word in user_input_lower for word in ["cold", "cool"]):
                return "increase_temperature"
            elif any(word in user_input_lower for word in ["hot", "warm"]):
                return "decrease_temperature"
            else:
                return "adjust_temperature"
        
        elif intent_type == IntentType.MUSIC_CONTROL:
            if "play" in user_input_lower:
                return "play_music"
            elif any(word in user_input_lower for word in ["stop", "pause"]):
                return "stop_music"
            else:
                return "control_music"
        
        elif intent_type == IntentType.WINDOW_CONTROL:
            if "open" in user_input_lower:
                return "open_window"
            elif "close" in user_input_lower:
                return "close_window"
            else:
                return "control_window"
        
        elif intent_type == IntentType.WEATHER_INQUIRY:
            return "get_weather_info"
        
        elif intent_type == IntentType.LOCATION_REQUEST:
            return "get_current_location"
        
        elif intent_type == IntentType.NAVIGATION:
            return "provide_navigation"
        
        else:
            return "general_conversation"
    
    def _get_available_tools(self, intent_type: IntentType) -> List[Dict[str, Any]]:
        """Get available tools with their schemas for the intent"""
        tools = []
        tool_names = self.intent_tool_mapping.get(intent_type, [])
        
        # Tool schemas (simplified for this implementation)
        tool_schemas = {
            "set_temperature": {
                "name": "set_temperature",
                "description": "Adjust cabin temperature",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "temperature": {"type": "number", "description": "Temperature in Celsius"}
                    },
                    "required": ["temperature"]
                }
            },
            "set_music": {
                "name": "set_music",
                "description": "Control music playback",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "track": {"type": "string", "description": "Song or artist name"}
                    },
                    "required": ["track"]
                }
            },
            "open_window": {
                "name": "open_window",
                "description": "Open or close windows",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "side": {"type": "string", "enum": ["left", "right"], "description": "Which side window"}
                    },
                    "required": ["side"]
                }
            },
            "adjust_seat": {
                "name": "adjust_seat",
                "description": "Adjust seat position",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "position": {"type": "string", "description": "Seat position"}
                    },
                    "required": ["position"]
                }
            },
            "get_weather": {
                "name": "get_weather",
                "description": "Get current weather information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "Location name"}
                    },
                    "required": ["location"]
                }
            },
            "get_location": {
                "name": "get_location",
                "description": "Get current GPS location",
                "parameters": {"type": "object", "properties": {}}
            },
            "play_spotify": {
                "name": "play_spotify",
                "description": "Play music via Spotify",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "track": {"type": "string", "description": "Song or artist name"}
                    },
                    "required": ["track"]
                }
            },
            "reroute": {
                "name": "reroute",
                "description": "Get new route to destination",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "destination": {"type": "string", "description": "Destination name"}
                    },
                    "required": ["destination"]
                }
            },
            "talk": {
                "name": "talk",
                "description": "Respond conversationally",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Message to communicate"}
                    },
                    "required": ["message"]
                }
            }
        }
        
        for tool_name in tool_names:
            if tool_name in tool_schemas:
                tools.append(tool_schemas[tool_name])
        
        return tools
    
    def _refine_tools_with_context(self, tools: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Refine tool selection based on current context"""
        # For now, return tools as-is
        # Future: Could filter based on current state
        return tools
    
    def _get_fallback_tools(self) -> List[Dict[str, Any]]:
        """Get fallback tools when intent classification fails"""
        return self._get_available_tools(IntentType.CONVERSATION)
    
    def get_intent_statistics(self) -> Dict[str, Any]:
        """Get statistics about intent classification"""
        return {
            "supported_intents": [intent.value for intent in IntentType],
            "total_patterns": sum(len(patterns) for patterns in self.intent_patterns.values()),
            "tool_mappings": {intent.value: tools for intent, tools in self.intent_tool_mapping.items()}
        }
