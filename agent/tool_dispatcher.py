"""
Tool Dispatcher Module
Maps intents to MCP tools and executes HTTP calls
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
import httpx
import os
from datetime import datetime

class ToolDispatcher:
    """
    Dispatches tool calls to appropriate MCP servers
    Handles HTTP communication and response processing
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # MCP Server endpoints
        self.mcp_servers = {
            "sim_actions": {
                "host": os.getenv("MCP_SIM_ACTIONS_HOST", "localhost"),
                "port": int(os.getenv("MCP_SIM_ACTIONS_PORT", 8001)),
                "tools": ["set_temperature", "set_music", "open_window", "adjust_seat"]
            },
            "sim_session": {
                "host": os.getenv("MCP_SIM_SESSION_HOST", "localhost"),
                "port": int(os.getenv("MCP_SIM_SESSION_PORT", 8002)),
                "tools": ["start_simulation", "pause_simulation", "reset_simulation", "log_event"]
            },
            "conversation": {
                "host": os.getenv("MCP_CONVERSATION_HOST", "localhost"),
                "port": int(os.getenv("MCP_CONVERSATION_PORT", 8003)),
                "tools": ["talk", "remember", "ask_confirm", "summarize"]
            },
            "external": {
                "host": os.getenv("MCP_EXTERNAL_HOST", "localhost"),
                "port": int(os.getenv("MCP_EXTERNAL_PORT", 8004)),
                "tools": ["get_weather", "get_location", "play_spotify", "reroute"]
            }
        }
        
        # HTTP client for API calls
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(float(os.getenv("REQUEST_TIMEOUT", 30)))
        )
        
        # Tool to server mapping
        self.tool_server_map = {}
        for server_name, config in self.mcp_servers.items():
            for tool in config["tools"]:
                self.tool_server_map[tool] = server_name
        
        self.logger.info("Tool Dispatcher initialized")
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by calling the appropriate MCP server
        """
        try:
            self.logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
            
            # Find the server for this tool
            server_name = self.tool_server_map.get(tool_name)
            if not server_name:
                raise ValueError(f"Tool '{tool_name}' not found in any MCP server")
            
            server_config = self.mcp_servers[server_name]
            
            # Build endpoint URL
            url = f"http://{server_config['host']}:{server_config['port']}/tools/{tool_name}"
            
            # Prepare request payload
            payload = {
                "tool": tool_name,
                "parameters": parameters,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": f"{tool_name}_{datetime.utcnow().timestamp()}"
            }
            
            # Make HTTP request to MCP server
            response = await self._make_http_request(url, payload)
            
            self.logger.info(f"Tool {tool_name} executed successfully")
            return response
            
        except Exception as e:
            self.logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "parameters": parameters
            }
    
    async def _make_http_request(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to MCP server with retry logic"""
        max_retries = int(os.getenv("RETRY_ATTEMPTS", 3))
        
        for attempt in range(max_retries):
            try:
                response = await self.http_client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    # Server or endpoint not found - might be offline
                    return await self._handle_offline_server(payload)
                else:
                    response.raise_for_status()
                    
            except httpx.ConnectError:
                self.logger.warning(f"Connection failed to {url}, attempt {attempt + 1}/{max_retries}")
                if attempt == max_retries - 1:
                    return await self._handle_offline_server(payload)
                await asyncio.sleep(1)  # Wait before retry
                
            except Exception as e:
                self.logger.error(f"HTTP request failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)
    
    async def _handle_offline_server(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle case when MCP server is offline - provide mock responses"""
        tool_name = payload["tool"]
        parameters = payload["parameters"]
        
        self.logger.warning(f"MCP server offline, providing mock response for {tool_name}")
        
        # Mock responses for development/testing
        mock_responses = {
            "set_temperature": {
                "success": True,
                "message": f"Temperature set to {parameters.get('temperature', 22)}°C",
                "current_temperature": parameters.get('temperature', 22),
                "mock": True
            },
            "set_music": {
                "success": True,
                "message": f"Now playing: {parameters.get('track', 'Unknown track')}",
                "current_track": parameters.get('track', 'Unknown track'),
                "mock": True
            },
            "open_window": {
                "success": True,
                "message": f"Window on {parameters.get('side', 'both')} side(s) opened",
                "window_state": f"{parameters.get('side', 'both')}_open",
                "mock": True
            },
            "adjust_seat": {
                "success": True,
                "message": f"Seat adjusted to {parameters.get('position', 'comfortable')} position",
                "seat_position": parameters.get('position', 'comfortable'),
                "mock": True
            },
            "get_weather": {
                "success": True,
                "location": parameters.get('location', 'Yalova, Turkey'),
                "temperature": 18,
                "condition": "Partly cloudy",
                "humidity": 65,
                "wind_speed": 12,
                "mock": True
            },
            "get_location": {
                "success": True,
                "latitude": 40.6553,
                "longitude": 29.2769,
                "location": "Yalova, Turkey",
                "address": "Rural area near Yalova",
                "mock": True
            },
            "play_spotify": {
                "success": True,
                "message": f"Playing {parameters.get('track', 'music')} on Spotify",
                "track": parameters.get('track', 'Unknown track'),
                "spotify_url": "spotify:track:mock",
                "mock": True
            },
            "reroute": {
                "success": True,
                "destination": parameters.get('destination', 'Unknown'),
                "estimated_time": "15 minutes",
                "distance": "8.5 km",
                "route": "Via rural roads",
                "mock": True
            },
            "start_simulation": {
                "success": True,
                "message": "Simulation started",
                "simulation_id": f"sim_{datetime.utcnow().timestamp()}",
                "status": "running",
                "mock": True
            },
            "pause_simulation": {
                "success": True,
                "message": "Simulation paused",
                "status": "paused",
                "mock": True
            },
            "reset_simulation": {
                "success": True,
                "message": "Simulation reset",
                "status": "reset",
                "mock": True
            },
            "log_event": {
                "success": True,
                "message": "Event logged",
                "event_id": f"event_{datetime.utcnow().timestamp()}",
                "mock": True
            },
            "talk": {
                "success": True,
                "message": "Message processed",
                "response": "I understand.",
                "mock": True
            },
            "remember": {
                "success": True,
                "message": "Preference saved",
                "key": parameters.get('key', 'unknown'),
                "value": parameters.get('value', 'unknown'),
                "mock": True
            },
            "ask_confirm": {
                "success": True,
                "message": "Confirmation requested",
                "prompt": parameters.get('prompt', 'Please confirm'),
                "mock": True
            },
            "summarize": {
                "success": True,
                "message": "Context summarized",
                "summary": "Recent activities include conversation and car adjustments.",
                "mock": True
            }
        }
        
        return mock_responses.get(tool_name, {
            "success": False,
            "error": f"Mock response not available for {tool_name}",
            "mock": True
        })
    
    async def check_server_health(self, server_name: str) -> Dict[str, Any]:
        """Check if an MCP server is healthy"""
        try:
            server_config = self.mcp_servers[server_name]
            url = f"http://{server_config['host']}:{server_config['port']}/health"
            
            response = await self.http_client.get(url)
            
            if response.status_code == 200:
                return {
                    "server": server_name,
                    "status": "healthy",
                    "response_time": response.elapsed.total_seconds()
                }
            else:
                return {
                    "server": server_name,
                    "status": "unhealthy",
                    "status_code": response.status_code
                }
                
        except Exception as e:
            return {
                "server": server_name,
                "status": "offline",
                "error": str(e)
            }
    
    async def check_all_servers_health(self) -> Dict[str, Any]:
        """Check health of all MCP servers"""
        health_checks = {}
        
        for server_name in self.mcp_servers.keys():
            health_checks[server_name] = await self.check_server_health(server_name)
        
        return health_checks
    
    async def get_available_tools(self, server_name: Optional[str] = None) -> Dict[str, Any]:
        """Get list of available tools from specified server or all servers"""
        if server_name:
            if server_name in self.mcp_servers:
                return {
                    "server": server_name,
                    "tools": self.mcp_servers[server_name]["tools"]
                }
            else:
                return {"error": f"Server {server_name} not found"}
        
        return {
            "servers": {
                name: config["tools"] 
                for name, config in self.mcp_servers.items()
            },
            "all_tools": list(self.tool_server_map.keys())
        }
    
    async def batch_execute_tools(self, tool_calls: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """Execute multiple tools concurrently"""
        tasks = []
        
        for tool_call in tool_calls:
            task = self.execute_tool(
                tool_call["name"], 
                tool_call.get("parameters", {})
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "tool": tool_calls[i]["name"]
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
        self.logger.info("Tool Dispatcher closed")
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get information about configured MCP servers"""
        return {
            "servers": self.mcp_servers,
            "tool_mapping": self.tool_server_map,
            "total_tools": len(self.tool_server_map),
            "total_servers": len(self.mcp_servers)
        }
