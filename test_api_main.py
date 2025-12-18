#!/usr/bin/env python3
"""
Test suite for api_main.py endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock pymodbus before importing api_main
mock_modbus_client = MagicMock()
sys.modules['pymodbus'] = MagicMock()
sys.modules['pymodbus.client'] = MagicMock()

from api_main import app, API_KEY


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_modbus():
    """Mock Modbus client"""
    with patch('api_main.mb_client') as mock:
        mock_client_instance = MagicMock()
        mock_client_instance.connect.return_value = True
        mock_client_instance.close.return_value = None
        
        # Mock successful read
        mock_read_result = MagicMock()
        mock_read_result.isError.return_value = False
        mock_read_result.registers = [1, 0, 0, 1, 0, 0, 0, 0]  # Sample registers
        mock_client_instance.read_holding_registers.return_value = mock_read_result
        
        # Mock successful write
        mock_write_result = MagicMock()
        mock_write_result.isError.return_value = False
        mock_client_instance.write_register.return_value = mock_write_result
        mock_client_instance.write_registers.return_value = mock_write_result
        
        mock.return_value = mock_client_instance
        yield mock


def test_status_unauthorized(client):
    """Test status endpoint without API key"""
    response = client.get("/status")
    assert response.status_code == 401


def test_status_authorized(client, mock_modbus):
    """Test status endpoint with valid API key"""
    response = client.get("/status", headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert "zone" in data
    assert "pump_on" in data
    assert "block_reason" in data


def test_manual_command_default_time(client, mock_modbus):
    """Test manual command validates zone and uses auto times"""
    response = client.post(
        "/command/manual",
        json={"zone": 2},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["zone"] == 2
    assert "note" in data  # Note about using auto times


def test_manual_command_custom_time(client, mock_modbus):
    """Test manual command ignores custom duration parameter"""
    response = client.post(
        "/command/manual",
        json={"zone": 3, "minutes": 10},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["zone"] == 3
    # minutes parameter is ignored - manual mode uses auto times


def test_manual_command_invalid_zone(client, mock_modbus):
    """Test manual command with invalid zone"""
    response = client.post(
        "/command/manual",
        json={"zone": 8},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 400


def test_manual_command_invalid_time(client, mock_modbus):
    """Test manual command with invalid time - now ignored as manual mode uses auto times"""
    response = client.post(
        "/command/manual",
        json={"zone": 1, "minutes": 300},
        headers={"X-API-Key": API_KEY}
    )
    # Time parameter is now ignored, so this should succeed
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True


def test_start_auto(client, mock_modbus):
    """Test start auto endpoint"""
    response = client.post(
        "/command/start-auto",
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True


def test_start_night_program(client, mock_modbus):
    """Test start night program endpoint"""
    response = client.post(
        "/command/start-night-program",
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "message" in data
    assert "alla zoner" in data["message"].lower()


def test_set_zone(client, mock_modbus):
    """Test set zone endpoint"""
    response = client.post(
        "/command/set-zone",
        json={"zone": 4},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["zone"] == 4


def test_set_manual_time(client, mock_modbus):
    """Test set manual time endpoint"""
    response = client.post(
        "/command/set-manual-time",
        json={"minutes": 15},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["minutes"] == 15


def test_stop(client, mock_modbus):
    """Test stop endpoint"""
    response = client.post(
        "/command/stop",
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True


def test_ui_endpoint(client):
    """Test UI endpoint returns HTML"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Bevattning" in response.text
    assert "Natt-program" in response.text
    assert "Manuell Styrning" in response.text


def test_test_bevattning_single_zone(client, mock_modbus):
    """Test zone testing endpoint for single zone"""
    response = client.post(
        "/menu/test-bevattning",
        json={"zone": 2, "duration_seconds": 1},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "test_results" in data
    assert data["zones_tested"] == [2]
    assert data["duration_per_zone"] == 1


def test_test_bevattning_all_zones(client, mock_modbus):
    """Test zone testing endpoint for all zones with confirmation"""
    response = client.post(
        "/menu/test-bevattning",
        json={"duration_seconds": 1, "all_zones_confirmed": True},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "test_results" in data
    assert len(data["zones_tested"]) == 7  # All 7 zones


def test_test_bevattning_all_zones_without_confirmation(client, mock_modbus):
    """Test zone testing endpoint for all zones requires confirmation"""
    response = client.post(
        "/menu/test-bevattning",
        json={"duration_seconds": 1},
        headers={"X-API-Key": API_KEY}
    )
    # Should fail without confirmation
    assert response.status_code == 400
    data = response.json()
    assert "all_zones_confirmed" in data["detail"]


def test_lagesval_auto_mode(client, mock_modbus):
    """Test mode selection - auto mode"""
    response = client.post(
        "/menu/lagesval?mode=1",
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["mode"] == "Auto"
    assert data["mode_value"] == 1


def test_lagesval_manual_mode(client, mock_modbus):
    """Test mode selection - manual mode"""
    response = client.post(
        "/menu/lagesval?mode=0",
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["mode"] == "Manual"
    assert data["mode_value"] == 0


def test_lagesval_invalid_mode(client, mock_modbus):
    """Test mode selection with invalid mode"""
    response = client.post(
        "/menu/lagesval?mode=5",
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 400


def test_felsokning(client, mock_modbus):
    """Test troubleshooting endpoint"""
    response = client.get(
        "/menu/felsökning",
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "block_reason" in data
    assert "block_reason_text" in data
    assert "events" in data
    assert "current_zone" in data


def test_reset_error(client, mock_modbus):
    """Test error reset endpoint"""
    response = client.post(
        "/menu/reset-error",
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["reset_performed"] is True
    assert "new_block_reason" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
