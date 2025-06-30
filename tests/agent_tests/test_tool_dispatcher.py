"""
Tests for Tool Dispatcher Module
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Mock external dependencies
sys.modules['httpx'] = Mock()

from agent.tool_dispatcher import ToolDispatcher

class TestToolDispatcher:
    """Test cases for ToolDispatcher"""
    
    @pytest.fixture
    def mock_http_client(self):
        """Mock HTTP client"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "message": "Test response"}
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.get = AsyncMock(return_value=mock_response)
        return mock_client
    
    @pytest.fixture
    def tool_dispatcher(self, mock_http_client):
        """Create ToolDispatcher instance with mocked HTTP client"""
        with patch.dict(os.environ, {
            'MCP_SIM_ACTIONS_HOST': 'localhost',
            'MCP_SIM_ACTIONS_PORT': '8001',
            'REQUEST_TIMEOUT': '30'
        }):
            dispatcher = ToolDispatcher()
            dispatcher.http_client = mock_http_client
            return dispatcher
    
    def test_tool_dispatcher_initialization(self, tool_dispatcher):
        """Test ToolDispatcher initialization"""
        assert tool_dispatcher is not None
        assert isinstance(tool_dispatcher.mcp_servers, dict)
        assert isinstance(tool_dispatcher.tool_server_map, dict)
        assert len(tool_dispatcher.mcp_servers) == 4  # 4 MCP servers
        assert len(tool_dispatcher.tool_server_map) > 0
    
    def test_tool_server_mapping(self, tool_dispatcher):
        """Test tool to server mapping"""
        assert "set_temperature" in tool_dispatcher.tool_server_map
        assert "get_weather" in tool_dispatcher.tool_server_map
        assert "start_simulation" in tool_dispatcher.tool_server_map
        assert "talk" in tool_dispatcher.tool_server_map
        
        assert tool_dispatcher.tool_server_map["set_temperature"] == "sim_actions"
        assert tool_dispatcher.tool_server_map["get_weather"] == "external"
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, tool_dispatcher, mock_http_client):
        """Test successful tool execution"""
        tool_name = "set_temperature"
        parameters = {"temperature": 24}
        
        result = await tool_dispatcher.execute_tool(tool_name, parameters)
        
        assert result["success"] is True
        assert "message" in result
        mock_http_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self, tool_dispatcher):
        """Test execution of unknown tool"""
        tool_name = "unknown_tool"
        parameters = {}
        
        result = await tool_dispatcher.execute_tool(tool_name, parameters)
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_execute_tool_server_offline(self, tool_dispatcher, mock_http_client):
        """Test tool execution when server is offline"""
        import httpx
        mock_http_client.post.side_effect = httpx.ConnectError("Connection failed")
        
        tool_name = "set_temperature"
        parameters = {"temperature": 24}
        
        result = await tool_dispatcher.execute_tool(tool_name, parameters)
        
        # Should return mock response when server is offline
        assert result["mock"] is True
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_handle_offline_server_temperature(self, tool_dispatcher):
        """Test offline server handling for temperature tool"""
        payload = {
            "tool": "set_temperature",
            "parameters": {"temperature": 25}
        }
        
        result = await tool_dispatcher._handle_offline_server(payload)
        
        assert result["success"] is True
        assert result["mock"] is True
        assert result["current_temperature"] == 25
    
    @pytest.mark.asyncio
    async def test_handle_offline_server_music(self, tool_dispatcher):
        """Test offline server handling for music tool"""
        payload = {
            "tool": "set_music",
            "parameters": {"track": "Test Song"}
        }
        
        result = await tool_dispatcher._handle_offline_server(payload)
        
        assert result["success"] is True
        assert result["mock"] is True
        assert result["current_track"] == "Test Song"
    
    @pytest.mark.asyncio
    async def test_handle_offline_server_weather(self, tool_dispatcher):
        """Test offline server handling for weather tool"""
        payload = {
            "tool": "get_weather",
            "parameters": {"location": "Yalova"}
        }
        
        result = await tool_dispatcher._handle_offline_server(payload)
        
        assert result["success"] is True
        assert result["mock"] is True
        assert "temperature" in result
        assert "condition" in result
    
    @pytest.mark.asyncio
    async def test_check_server_health_healthy(self, tool_dispatcher, mock_http_client):
        """Test server health check when server is healthy"""
        server_name = "sim_actions"
        
        result = await tool_dispatcher.check_server_health(server_name)
        
        assert result["server"] == server_name
        assert result["status"] == "healthy"
        mock_http_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_server_health_offline(self, tool_dispatcher, mock_http_client):
        """Test server health check when server is offline"""
        import httpx
        mock_http_client.get.side_effect = httpx.ConnectError("Connection failed")
        
        server_name = "sim_actions"
        
        result = await tool_dispatcher.check_server_health(server_name)
        
        assert result["server"] == server_name
        assert result["status"] == "offline"
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_check_all_servers_health(self, tool_dispatcher):
        """Test health check for all servers"""
        # Mock the individual health check method
        tool_dispatcher.check_server_health = AsyncMock(return_value={
            "status": "healthy"
        })
        
        result = await tool_dispatcher.check_all_servers_health()
        
        assert isinstance(result, dict)
        assert len(result) == 4  # 4 servers
        assert all("status" in health for health in result.values())
    
    @pytest.mark.asyncio
    async def test_get_available_tools_all(self, tool_dispatcher):
        """Test getting all available tools"""
        result = await tool_dispatcher.get_available_tools()
        
        assert "servers" in result
        assert "all_tools" in result
        assert isinstance(result["all_tools"], list)
        assert len(result["all_tools"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_available_tools_specific_server(self, tool_dispatcher):
        """Test getting tools for specific server"""
        server_name = "sim_actions"
        
        result = await tool_dispatcher.get_available_tools(server_name)
        
        assert result["server"] == server_name
        assert "tools" in result
        assert isinstance(result["tools"], list)
        assert "set_temperature" in result["tools"]
    
    @pytest.mark.asyncio
    async def test_get_available_tools_invalid_server(self, tool_dispatcher):
        """Test getting tools for invalid server"""
        server_name = "invalid_server"
        
        result = await tool_dispatcher.get_available_tools(server_name)
        
        assert "error" in result
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_batch_execute_tools(self, tool_dispatcher):
        """Test batch execution of tools"""
        tool_calls = [
            {"name": "set_temperature", "parameters": {"temperature": 24}},
            {"name": "set_music", "parameters": {"track": "Test Song"}}
        ]
        
        # Mock execute_tool method
        tool_dispatcher.execute_tool = AsyncMock(return_value={"success": True})
        
        results = await tool_dispatcher.batch_execute_tools(tool_calls)
        
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(result["success"] for result in results)
    
    @pytest.mark.asyncio
    async def test_batch_execute_tools_with_error(self, tool_dispatcher):
        """Test batch execution with some tools failing"""
        tool_calls = [
            {"name": "set_temperature", "parameters": {"temperature": 24}},
            {"name": "invalid_tool", "parameters": {}}
        ]
        
        async def mock_execute(name, params):
            if name == "invalid_tool":
                raise ValueError("Tool not found")
            return {"success": True}
        
        tool_dispatcher.execute_tool = mock_execute
        
        results = await tool_dispatcher.batch_execute_tools(tool_calls)
        
        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False
    
    def test_get_server_info(self, tool_dispatcher):
        """Test getting server information"""
        info = tool_dispatcher.get_server_info()
        
        assert "servers" in info
        assert "tool_mapping" in info
        assert "total_tools" in info
        assert "total_servers" in info
        assert info["total_servers"] == 4
        assert info["total_tools"] > 0
    
    @pytest.mark.asyncio
    async def test_close(self, tool_dispatcher, mock_http_client):
        """Test closing the dispatcher"""
        mock_http_client.aclose = AsyncMock()
        
        await tool_dispatcher.close()
        
        mock_http_client.aclose.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__])
