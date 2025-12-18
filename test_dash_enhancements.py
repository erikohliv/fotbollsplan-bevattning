#!/usr/bin/env python3
"""
Test suite for Dash Process View enhancements
Tests the new /process-view and /zone-control endpoints
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock pymodbus before importing api_main
sys.modules['pymodbus'] = MagicMock()
sys.modules['pymodbus.client'] = MagicMock()

from api_main import app, API_KEY


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_modbus():
    """Mock Modbus client with realistic data"""
    with patch('api_main.mb_client') as mock:
        mock_client_instance = MagicMock()
        mock_client_instance.connect.return_value = True
        mock_client_instance.close.return_value = None
        
        def mock_read(address, count, unit):
            """Mock read based on address"""
            result = MagicMock()
            result.isError.return_value = False
            
            # MW50-53: Status registers
            if address == 50:
                result.registers = [2, 1, 3, 2]  # zone=2, pump=on, steg=3, selected=2
            # MW70-73: Heartbeat and error registers
            elif address == 70:
                result.registers = [1, 100, 0x04, 0]  # heartbeat, count, eventmask, block_reason=0 (OK)
            # MW20-21: Config
            elif address == 20:
                result.registers = [30, 15]  # tid_center=30, tid_horn=15
            # MW30-32: Environment
            elif address == 30:
                result.registers = [45, 2, 18]  # moisture=45%, rain=2mm, temp=18C
            # MW100: Mode
            elif address == 100:
                result.registers = [2]  # Fjärrläge
            else:
                result.registers = [0] * count
            
            return result
        
        mock_client_instance.read_holding_registers.side_effect = mock_read
        
        # Mock successful write
        mock_write_result = MagicMock()
        mock_write_result.isError.return_value = False
        mock_client_instance.write_register.return_value = mock_write_result
        
        mock.return_value = mock_client_instance
        yield mock


def test_process_view_structure(client, mock_modbus):
    """Test that /process-view returns correctly formatted data"""
    response = client.get("/process-view", headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    
    data = response.json()
    assert data.get('ok') == True
    
    # Check zones
    assert 'zones' in data
    assert len(data['zones']) == 7
    for zone in data['zones']:
        assert 'zone' in zone
        assert 'active' in zone
        assert 'selected' in zone
    
    # Check pump
    assert 'pump' in data
    assert 'on' in data['pump']
    assert 'status' in data['pump']
    
    # Check sequence
    assert 'sequence' in data
    assert 'active' in data['sequence']
    assert 'current_step' in data['sequence']
    assert 'current_zone' in data['sequence']
    
    # Check errors and error_details (NEW)
    assert 'errors' in data
    assert 'error_details' in data
    
    # Verify error_details structure
    error_details = data['error_details']
    for error_key in ['e_stop', 'moisture_block', 'rain_block', 'anti_collision', 'sequence_active']:
        assert error_key in error_details
        assert 'active' in error_details[error_key]
        assert 'text' in error_details[error_key]
        assert 'explanation' in error_details[error_key]
        assert 'severity' in error_details[error_key]
    
    # Check block_status with explanation (NEW)
    assert 'block_status' in data
    assert 'code' in data['block_status']
    assert 'text' in data['block_status']
    assert 'explanation' in data['block_status']  # NEW FIELD
    assert 'blocked' in data['block_status']
    
    # Check environment
    assert 'environment' in data
    assert 'moisture_percent' in data['environment']
    assert 'rain_24h_mm' in data['environment']
    assert 'temperature_c' in data['environment']
    
    # Check configuration
    assert 'configuration' in data
    assert 'tid_center_min' in data['configuration']
    assert 'tid_horn_min' in data['configuration']
    
    # Check mode
    assert 'mode' in data
    assert 'value' in data['mode']
    assert 'text' in data['mode']


def test_process_view_error_details_severity(client, mock_modbus):
    """Test that error_details include severity levels"""
    response = client.get("/process-view", headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    
    data = response.json()
    error_details = data['error_details']
    
    # Check severity levels are valid
    valid_severities = ['critical', 'warning', 'info']
    for error_info in error_details.values():
        assert error_info['severity'] in valid_severities
    
    # E-stop should be critical
    assert error_details['e_stop']['severity'] == 'critical'
    
    # Blocks should be warning
    assert error_details['moisture_block']['severity'] == 'warning'
    assert error_details['rain_block']['severity'] == 'warning'
    
    # Anti-collision and sequence should be info
    assert error_details['anti_collision']['severity'] == 'info'
    assert error_details['sequence_active']['severity'] == 'info'


def test_process_view_block_explanation(client, mock_modbus):
    """Test that block_status includes detailed explanation"""
    response = client.get("/process-view", headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    
    data = response.json()
    block_status = data['block_status']
    
    # Should have explanation field
    assert 'explanation' in block_status
    assert isinstance(block_status['explanation'], str)
    assert len(block_status['explanation']) > 0
    
    # For OK status (code 0), should mention no blockages
    if block_status['code'] == 0:
        assert 'normalt' in block_status['explanation'].lower() or 'inga' in block_status['explanation'].lower()


def test_zone_control_start(client, mock_modbus):
    """Test zone-control start action"""
    response = client.post(
        "/zone-control",
        json={"zone": 3, "action": "start"},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data.get('ok') == True
    assert data.get('action') == 'start'
    assert data.get('zone') == 3
    assert 'message' in data


def test_zone_control_stop(client, mock_modbus):
    """Test zone-control stop action"""
    response = client.post(
        "/zone-control",
        json={"zone": 5, "action": "stop"},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data.get('ok') == True
    assert data.get('action') == 'stop'
    assert 'message' in data


def test_zone_control_invalid_action(client, mock_modbus):
    """Test zone-control with invalid action"""
    response = client.post(
        "/zone-control",
        json={"zone": 2, "action": "invalid"},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 400
    assert "Ogiltig åtgärd" in response.json()['detail']


def test_zone_control_invalid_zone(client, mock_modbus):
    """Test zone-control with invalid zone number"""
    response = client.post(
        "/zone-control",
        json={"zone": 10, "action": "start"},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 400
    assert "zone must be 1..7" in response.json()['detail']


def test_rain_forecast_structure(client):
    """Test that /rain-forecast returns correctly formatted data"""
    with patch('api_main.requests.get') as mock_get:
        # Mock Open-Meteo responses
        mock_forecast_response = MagicMock()
        mock_forecast_response.status_code = 200
        mock_forecast_response.json.return_value = {
            "hourly": {
                "time": ["2025-12-18T20:00", "2025-12-18T21:00"],
                "precipitation": [0.5, 1.2]
            }
        }
        
        mock_historical_response = MagicMock()
        mock_historical_response.status_code = 200
        mock_historical_response.json.return_value = {
            "daily": {
                "time": ["2025-12-11", "2025-12-12"],
                "precipitation_sum": [2.0, 0.5]
            }
        }
        
        mock_get.side_effect = [mock_forecast_response, mock_historical_response]
        
        response = client.get("/rain-forecast", headers={"X-API-Key": API_KEY})
        assert response.status_code == 200
        
        data = response.json()
        assert data.get('ok') == True
        
        # Check forecast_24h
        assert 'forecast_24h' in data
        assert 'total_mm' in data['forecast_24h']
        assert 'hourly' in data['forecast_24h']
        
        # Check history_7d
        assert 'history_7d' in data
        assert 'daily' in data['history_7d']
        
        # Check location
        assert 'location' in data
        assert 'latitude' in data['location']
        assert 'longitude' in data['location']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
