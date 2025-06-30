"""
Integration tests for Project Caesar
Tests the complete agent workflow end-to-end
"""

import sys
import os
import asyncio
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock external dependencies
mock_packages = ['openai', 'anthropic', 'dotenv', 'httpx', 'pyttsx3']
for package in mock_packages:
    sys.modules[package] = Mock()

# Special mocks
openai_mock = Mock()
openai_mock.OpenAI = Mock()
sys.modules['openai'] = openai_mock

from agent.agent_core import AgentCore, AgentResponse

class TestIntegration:
    """Integration tests for the complete agent system"""
    
    def setup_mocks(self):
        """Set up comprehensive mocks for testing"""
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "I'll adjust the temperature for you."
        mock_response.choices[0].message.function_call = Mock()
        mock_response.choices[0].message.function_call.name = "set_temperature"
        mock_response.choices[0].message.function_call.arguments = '{"temperature": 24}'
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        
        return mock_client
    
    async def test_complete_conversation_flow(self):
        """Test a complete conversation flow from input to response"""
        print("\n🔄 Testing Complete Conversation Flow")
        print("-" * 40)
        
        # Set up environment
        with patch.dict(os.environ, {
            'AGENT_MODEL': 'gpt-4-turbo-preview',
            'OPENAI_API_KEY': 'test-key',
            'MCP_SIM_ACTIONS_HOST': 'localhost',
            'MCP_SIM_ACTIONS_PORT': '8001'
        }):
            # Create agent with mocked dependencies
            mock_client = self.setup_mocks()
            
            with patch('agent.agent_core.openai.OpenAI', return_value=mock_client):
                agent = AgentCore()
                
                # Test input: temperature adjustment
                user_input = "It's cold in here, please set temperature to 24 degrees"
                
                print(f"👤 User Input: {user_input}")
                
                # Process the input
                response = await agent.process_input(user_input)
                
                print(f"🤖 Agent Response: {response.message}")
                print(f"🔧 Action Taken: {response.action_taken}")
                print(f"🛠️  Tool Calls: {len(response.tool_calls)} tool(s) executed")
                
                # Verify response
                assert isinstance(response, AgentResponse)
                assert response.message is not None
                assert len(response.message) > 0
                
                # Check conversation history
                history = agent.get_conversation_history()
                assert len(history) >= 2  # User input + agent response
                
                print("✅ Complete conversation flow: PASSED")
                return True
    
    async def test_multiple_intents(self):
        """Test handling multiple different types of intents"""
        print("\n🎯 Testing Multiple Intent Types")
        print("-" * 40)
        
        with patch.dict(os.environ, {
            'AGENT_MODEL': 'gpt-4-turbo-preview',
            'OPENAI_API_KEY': 'test-key'
        }):
            mock_client = self.setup_mocks()
            
            with patch('agent.agent_core.openai.OpenAI', return_value=mock_client):
                agent = AgentCore()
                
                # Test different types of inputs
                test_inputs = [
                    ("It's too hot, cool it down", "temperature_control"),
                    ("Play some jazz music", "music_control"),
                    ("Open the left window", "window_control"),
                    ("What's the weather like?", "weather_inquiry"),
                    ("Where are we?", "location_request"),
                    ("Hello, how are you?", "conversation")
                ]
                
                for user_input, expected_intent in test_inputs:
                    print(f"Testing: {user_input}")
                    
                    # Get intent classification
                    context = await agent.state_tracker.get_current_context()
                    intent_result = await agent.intent_router.route_intent(user_input, context)
                    
                    print(f"  Intent: {intent_result['intent_type']} (confidence: {intent_result['confidence']:.2f})")
                    print(f"  Tools: {intent_result['suggested_tools']}")
                    
                    # Verify intent is reasonable
                    assert intent_result['confidence'] > 0
                    assert len(intent_result['suggested_tools']) > 0
                
                print("✅ Multiple intent handling: PASSED")
                return True
    
    async def test_state_persistence(self):
        """Test state tracking and persistence"""
        print("\n💾 Testing State Persistence")
        print("-" * 40)
        
        agent = AgentCore()
        
        # Initial state
        initial_context = await agent.state_tracker.get_current_context()
        print(f"Initial temperature: {initial_context['environment']['temperature']}°C")
        
        # Simulate tool execution that changes state
        tool_results = [{
            "success": True,
            "tool": "set_temperature",
            "arguments": {"temperature": 26},
            "result": {"current_temperature": 26}
        }]
        
        # Update context
        await agent.state_tracker.update_context(
            "Set temperature to 26",
            "Temperature set to 26°C",
            tool_results
        )
        
        # Check updated state
        updated_context = await agent.state_tracker.get_current_context()
        print(f"Updated temperature: {updated_context['environment']['temperature']}°C")
        
        assert updated_context['environment']['temperature'] == 26
        
        # Test preference storage
        await agent.state_tracker.remember_preference("preferred_temperature", 25.0)
        stored_pref = await agent.state_tracker.get_preference("preferred_temperature")
        
        print(f"Stored preference: {stored_pref}°C")
        assert stored_pref == 25.0
        
        print("✅ State persistence: PASSED")
        return True
    
    async def test_error_handling(self):
        """Test error handling and fallback mechanisms"""
        print("\n⚠️  Testing Error Handling")
        print("-" * 40)
        
        agent = AgentCore()
        
        # Test invalid tool execution
        try:
            result = await agent.tool_dispatcher.execute_tool("invalid_tool", {})
            print(f"Invalid tool result: {result['success']}")
            assert result['success'] is False
            print("✅ Invalid tool handling: PASSED")
        except Exception as e:
            print(f"❌ Error handling failed: {str(e)}")
            return False
        
        # Test empty/invalid input
        try:
            response = await agent.process_input("")
            print(f"Empty input handled: {response.message is not None}")
            assert response.message is not None
            print("✅ Empty input handling: PASSED")
        except Exception as e:
            print(f"❌ Empty input handling failed: {str(e)}")
            return False
        
        print("✅ Error handling: PASSED")
        return True
    
    def test_tool_dispatcher_comprehensive(self):
        """Test tool dispatcher with all server types"""
        print("\n🔧 Testing Tool Dispatcher Comprehensively")
        print("-" * 40)
        
        from agent.tool_dispatcher import ToolDispatcher
        
        dispatcher = ToolDispatcher()
        
        # Test server configuration
        print(f"Configured servers: {len(dispatcher.mcp_servers)}")
        print(f"Total tools mapped: {len(dispatcher.tool_server_map)}")
        
        # Test tool mapping for each server
        expected_tools = {
            "sim_actions": ["set_temperature", "set_music", "open_window", "adjust_seat"],
            "sim_session": ["start_simulation", "pause_simulation", "reset_simulation", "log_event"],
            "conversation": ["talk", "remember", "ask_confirm", "summarize"],
            "external": ["get_weather", "get_location", "play_spotify", "reroute"]
        }
        
        for server, tools in expected_tools.items():
            for tool in tools:
                assert tool in dispatcher.tool_server_map
                assert dispatcher.tool_server_map[tool] == server
                print(f"  ✓ {tool} → {server}")
        
        # Test server info
        info = dispatcher.get_server_info()
        assert info['total_servers'] == 4
        assert info['total_tools'] > 0
        
        print("✅ Tool dispatcher comprehensive: PASSED")
        return True
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Project Caesar - Integration Tests")
        print("=" * 50)
        
        test_methods = [
            ("Complete Conversation Flow", self.test_complete_conversation_flow),
            ("Multiple Intent Types", self.test_multiple_intents),
            ("State Persistence", self.test_state_persistence),
            ("Error Handling", self.test_error_handling),
            ("Tool Dispatcher", lambda: self.test_tool_dispatcher_comprehensive())
        ]
        
        results = []
        
        for test_name, test_method in test_methods:
            try:
                if asyncio.iscoroutinefunction(test_method):
                    result = await test_method()
                else:
                    result = test_method()
                
                results.append((test_name, "PASSED" if result else "FAILED"))
                
            except Exception as e:
                print(f"❌ {test_name}: FAILED - {str(e)}")
                results.append((test_name, f"FAILED - {str(e)}"))
        
        # Print summary
        print("\n" + "=" * 50)
        print("📋 INTEGRATION TEST SUMMARY")
        print("=" * 50)
        
        passed = 0
        failed = 0
        
        for test_name, status in results:
            if "PASSED" in status:
                print(f"✅ {test_name}: {status}")
                passed += 1
            else:
                print(f"❌ {test_name}: {status}")
                failed += 1
        
        print(f"\n📊 Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("🎉 All integration tests passed!")
            print("\n🎊 Project Caesar Agent System is ready!")
            print("=" * 50)
            return True
        else:
            print("⚠️  Some integration tests failed.")
            return False

def run_integration_tests():
    """Run integration tests (non-async wrapper)"""
    return asyncio.run(main())

async def main():
    """Run integration tests"""
    test_suite = TestIntegration()
    success = await test_suite.run_all_tests()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
