import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock
from modules.core.orchestrator import orchestrate_data, get_circuit_breaker, monitor, DataQualityMonitor

# Helper to reset monitor and circuit breakers
@pytest.fixture(autouse=True)
def reset_state():
    global monitor
    monitor.records.clear()
    cb = get_circuit_breaker("TestModule")
    cb.record_success()
    yield

# Dummy fallback function
def fallback_dummy():
    return [{"id": 1, "value": "fallback"}]

def test_success_path():
    @orchestrate_data("TestModule", fallback_dummy, timeout=1.0, max_retries=1)
    def fetch_real():
        return [{"id": 1, "value": "real"}]

    result = fetch_real()
    assert result[0]["value"] == "real"
    report = monitor.get_daily_report()
    assert report["real_data_coverage"] == 100.0
    assert report["fallback_count"] == 0

def test_fallback_on_exception():
    @orchestrate_data("TestModule", fallback_dummy, timeout=1.0, max_retries=2)
    def fetch_error():
        raise ValueError("Simulated API Error")

    result = fetch_error()
    assert result[0]["value"] == "fallback"
    report = monitor.get_daily_report()
    assert report["real_data_coverage"] == 0.0
    assert report["fallback_count"] == 1

def test_circuit_breaker_trips():
    cb = get_circuit_breaker("TestModule")
    cb.failure_threshold = 3
    
    @orchestrate_data("TestModule", fallback_dummy, timeout=1.0, max_retries=1)
    def fetch_error():
        raise ValueError("Simulated API Error")

    # Trip the breaker
    fetch_error()
    fetch_error()
    fetch_error()
    
    assert cb.state == "OPEN"
    
    # Next call should be rejected immediately without calling the function
    # To prove this, we could use a mock, but since the result is fallback anyway, we can just check state
    result = fetch_error()
    assert result[0]["value"] == "fallback"
    assert cb.state == "OPEN"

def test_timeout_fallback():
    @orchestrate_data("TestModule", fallback_dummy, timeout=0.1, max_retries=1)
    def fetch_slow():
        time.sleep(0.2)
        return [{"id": 1, "value": "real"}]

    result = fetch_slow()
    assert result[0]["value"] == "fallback"

@pytest.mark.asyncio
async def test_async_orchestrator():
    async def async_fallback():
        return [{"id": 1, "value": "fallback"}]

    @orchestrate_data("TestModuleAsync", async_fallback, timeout=1.0, max_retries=1)
    async def fetch_async():
        await asyncio.sleep(0.01)
        return [{"id": 1, "value": "real"}]

    result = await fetch_async()
    assert result[0]["value"] == "real"
