import pytest
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from toaster.cli import _run_init_async

@pytest.mark.asyncio
@patch('toaster.cli.GeminiClient')
async def test_init_command(mock_client_class):
    mock_client = MagicMock()
    # Mock generation just so it doesn't try calling if it triggers
    mock_client.generate_description = AsyncMock(return_value={"status": "error"})
    mock_client_class.return_value = mock_client
    
    test_dir = os.path.join(os.path.dirname(__file__), "../test_code/MockProject")
    cache_file = os.path.join(test_dir, ".toaster_cache.json")
    
    if os.path.exists(cache_file):
        os.remove(cache_file)
        
    await _run_init_async(
        target_path=test_dir,
        skeleton=False,
        use_cache=True
    )
    
    assert os.path.exists(cache_file)
    
@pytest.mark.asyncio
@patch('toaster.cli.GeminiClient')
async def test_cache_loading(mock_client_class):
    mock_client = MagicMock()
    
    # Needs to return a valid payload so `.description` is fulfilled and cached correctly.
    mock_client.generate_description = AsyncMock(return_value={
        "status": "success",
        "description": "Mocked Class Description.",
        "confidence": 0.8,
        "methods": [
            {
                "umid": "Target#hello()",
                "description": "Mocked Method Description.",
                "confidence": 0.9
            }
        ]
    })
    
    mock_client_class.return_value = mock_client
    
    test_dir = os.path.join(os.path.dirname(__file__), "../test_code/MockProject")
    cache_file = os.path.join(test_dir, ".toaster_cache.json")
    if os.path.exists(cache_file):
        os.remove(cache_file)
    
    # Run the init twice. 
    # The first time builds the cache format even though the internal LLM generation fails mockingly
    await _run_init_async(
        target_path=test_dir,
        skeleton=False,
        use_cache=True
    )
    
    # Reset mock after first initialization pass
    mock_client.generate_description.reset_mock()
    
    # Run it again, use_cache=True should completely avoid calling generate_description
    await _run_init_async(
        target_path=test_dir,
        skeleton=False,
        use_cache=True
    )
    
    # Ensure LLM wasn't called because everything was pulled from cache
    mock_client.generate_description.assert_not_called()
