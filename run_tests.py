#!/usr/bin/env python3
"""
Test runner for Project Caesar
Handles dependency mocking and test execution
"""

import sys
import os
import subprocess
from unittest.mock import Mock

def setup_mocks():
    """Set up mocks for external dependencies"""
    
    # Mock external packages that may not be installed
    mock_packages = [
        'openai',
        'anthropic', 
        'dotenv',
        'httpx',
        'pyttsx3',
        'pytest',
        'spotipy',
        'pygame',
        'structlog',
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'alembic'
    ]
    
    for package in mock_packages:
        if package not in sys.modules:
            sys.modules[package] = Mock()
    
    # Special mocks for specific modules
    openai_mock = Mock()
    openai_mock.OpenAI = Mock()
    sys.modules['openai'] = openai_mock
    
    anthropic_mock = Mock()
    anthropic_mock.Anthropic = Mock()
    sys.modules['anthropic'] = anthropic_mock
    
    httpx_mock = Mock()
    httpx_mock.AsyncClient = Mock()
    httpx_mock.Timeout = Mock()
    httpx_mock.ConnectError = Exception
    sys.modules['httpx'] = httpx_mock
    
    dotenv_mock = Mock()
    dotenv_mock.load_dotenv = Mock()
    sys.modules['dotenv'] = dotenv_mock
    
    pyttsx3_mock = Mock()
    pyttsx3_mock.init = Mock()
    sys.modules['pyttsx3'] = pyttsx3_mock

def run_simple_tests():
    """Run simple tests without pytest"""
    print("🚀 Running Project Caesar Tests")
    print("=" * 50)
    
    # Setup mocks
    setup_mocks()
    
    # Add project root to path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # Import and test modules
    test_results = []
    
    try:
        print("\n📝 Testing Agent Core...")
        from agent.agent_core import AgentCore, AgentResponse
        
        # Test AgentResponse creation
        response = AgentResponse(message="Test", action_taken="test")
        assert response.message == "Test"
        assert response.action_taken == "test"
        print("✅ AgentResponse creation: PASSED")
        
        # Test AgentCore initialization 
        with MockEnvironment():
            agent = AgentCore()
            assert agent is not None
            assert hasattr(agent, 'intent_router')
            assert hasattr(agent, 'tool_dispatcher')
            print("✅ AgentCore initialization: PASSED")
        
        test_results.append(("AgentCore", "PASSED"))
        
    except Exception as e:
        print(f"❌ AgentCore tests: FAILED - {str(e)}")
        test_results.append(("AgentCore", f"FAILED - {str(e)}"))
    
    try:
        print("\n🎯 Testing Intent Router...")
        from agent.intent_router import IntentRouter, IntentType
        
        router = IntentRouter()
        assert router is not None
        assert len(router.intent_patterns) > 0
        print("✅ IntentRouter initialization: PASSED")
        
        # Test intent classification
        result = router._classify_intent("it's too cold")
        assert result.intent_type == IntentType.TEMPERATURE_CONTROL
        print("✅ Intent classification: PASSED")
        
        test_results.append(("IntentRouter", "PASSED"))
        
    except Exception as e:
        print(f"❌ IntentRouter tests: FAILED - {str(e)}")
        test_results.append(("IntentRouter", f"FAILED - {str(e)}"))
    
    try:
        print("\n🔧 Testing Tool Dispatcher...")
        from agent.tool_dispatcher import ToolDispatcher
        
        with MockEnvironment():
            dispatcher = ToolDispatcher()
            assert dispatcher is not None
            assert len(dispatcher.mcp_servers) == 4
            assert len(dispatcher.tool_server_map) > 0
            print("✅ ToolDispatcher initialization: PASSED")
            
            # Test tool mapping
            assert "set_temperature" in dispatcher.tool_server_map
            assert dispatcher.tool_server_map["set_temperature"] == "sim_actions"
            print("✅ Tool mapping: PASSED")
        
        test_results.append(("ToolDispatcher", "PASSED"))
        
    except Exception as e:
        print(f"❌ ToolDispatcher tests: FAILED - {str(e)}")
        test_results.append(("ToolDispatcher", f"FAILED - {str(e)}"))
    
    try:
        print("\n💬 Testing Dialogue Handler...")
        from agent.dialogue_handler import DialogueHandler
        
        with MockEnvironment():
            handler = DialogueHandler()
            assert handler is not None
            assert len(handler.greetings) > 0
            print("✅ DialogueHandler initialization: PASSED")
            
            # Test greeting
            import asyncio
            async def test_greeting():
                greeting = await handler.get_greeting()
                assert isinstance(greeting, str)
                assert len(greeting) > 0
                return True
            
            result = asyncio.run(test_greeting())
            assert result is True
            print("✅ Greeting generation: PASSED")
        
        test_results.append(("DialogueHandler", "PASSED"))
        
    except Exception as e:
        print(f"❌ DialogueHandler tests: FAILED - {str(e)}")
        test_results.append(("DialogueHandler", f"FAILED - {str(e)}"))
    
    try:
        print("\n📊 Testing State Tracker...")
        from agent.state_tracker import StateTracker, EnvironmentState, UserPreferences
        
        # Test dataclasses
        env_state = EnvironmentState()
        assert env_state.temperature == 22.0
        assert env_state.music_playing is False
        print("✅ EnvironmentState creation: PASSED")
        
        user_prefs = UserPreferences()
        assert user_prefs.preferred_temperature == 22.0
        assert user_prefs.language == "en"
        print("✅ UserPreferences creation: PASSED")
        
        # Test StateTracker
        tracker = StateTracker()
        assert tracker is not None
        assert isinstance(tracker.environment_state, EnvironmentState)
        assert isinstance(tracker.user_preferences, UserPreferences)
        print("✅ StateTracker initialization: PASSED")
        
        test_results.append(("StateTracker", "PASSED"))
        
    except Exception as e:
        print(f"❌ StateTracker tests: FAILED - {str(e)}")
        test_results.append(("StateTracker", f"FAILED - {str(e)}"))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for module, status in test_results:
        if "PASSED" in status:
            print(f"✅ {module}: {status}")
            passed += 1
        else:
            print(f"❌ {module}: {status}")
            failed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return False

class MockEnvironment:
    """Context manager for mocking environment variables"""
    
    def __enter__(self):
        self.original_env = os.environ.copy()
        
        # Set test environment variables
        os.environ.update({
            'AGENT_MODEL': 'gpt-4-turbo-preview',
            'AGENT_TEMPERATURE': '0.7',
            'AGENT_MAX_TOKENS': '2048',
            'OPENAI_API_KEY': 'test-key',
            'MCP_SIM_ACTIONS_HOST': 'localhost',
            'MCP_SIM_ACTIONS_PORT': '8001',
            'TTS_ENGINE': 'pyttsx3',
            'TTS_VOICE_RATE': '200',
            'TTS_VOICE_VOLUME': '0.8'
        })
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

def main():
    """Main test runner"""
    print("Project Caesar - Test Runner")
    print("Checking for pytest...")
    
    # Try to run with pytest if available
    try:
        import pytest
        print("✅ pytest found, running full test suite...")
        
        # Setup mocks first
        setup_mocks()
        
        # Run pytest
        result = pytest.main([
            "tests/",
            "-v",
            "--tb=short",
            "--disable-warnings"
        ])
        
        if result == 0:
            print("🎉 All pytest tests passed!")
        else:
            print("⚠️  Some pytest tests failed.")
            
        return result == 0
        
    except ImportError:
        print("⚠️  pytest not found, running simple tests...")
        return run_simple_tests()

def run_tests():
    """Wrapper function for main() to maintain compatibility"""
    return main()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
