#!/usr/bin/env python3
"""
Test suite for api_main.py endpoints
"""

import pytest
import logging
import requests
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

from api_main import (
    API_KEY,
    API_LOGGER_NAME,
    MW_BLOCK_REASON,
    MW_FLOW_ALARM,
    MW_FLOW_SWITCH,
    MW_HEARTBEAT,
    MW_MODE,
    MW_MODE_OVERRIDE,
    MW_PRESSURE_ALARM,
    MW_PRESSURE_SWITCH,
    MW_STATUS_ZONE,
    MW_TEST_ZONE_RESULT,
    USER_MODBUS_ERROR,
    app,
)


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
        
        # Mock successful read with address-aware side effect
        def _make_result(values):
            result = MagicMock()
            result.isError.return_value = False
            result.registers = values
            return result

        def _read_side_effect(address, count=1, unit=None):
            defaults = {
                MW_STATUS_ZONE: [1, 0, 0, 1],
                # MW54-56 maps to: [MW54=pressure_alarm, MW55=flow_switch, MW56=flow_alarm]
                MW_PRESSURE_ALARM: [0, 1, 0],
                MW_HEARTBEAT: [0, 0, 0, 0],
                MW_MODE: [0],
                MW_MODE_OVERRIDE: [1],
                MW_PRESSURE_SWITCH: [1],
                MW_BLOCK_REASON: [0],
                MW_TEST_ZONE_RESULT: [0],
            }
            values = defaults.get(address, [0] * count)
            if len(values) < count:
                values = values + [0] * (count - len(values))
            return _make_result(values[:count])

        mock_client_instance.read_holding_registers.side_effect = _read_side_effect
        
        # Mock successful write
        mock_write_result = MagicMock()
        mock_write_result.isError.return_value = False
        mock_client_instance.write_register.return_value = mock_write_result
        mock_client_instance.write_registers.return_value = mock_write_result
        
        mock.return_value = mock_client_instance
        yield mock_client_instance


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
    assert "safety" in data
    assert "pressure_switch" in data
    assert "pressure_alarm" in data
    assert "flow_switch" in data
    assert "flow_alarm" in data


@pytest.mark.parametrize(
    "pressure_alarm, flow_alarm, pressure_ok, flow_ok, pump_on, expected_flags",
    [
        # Normal operation: all OK
        (0, 0, 1, 1, 1, {"tryck_timeout": False, "oväntat_tryck": False, "torrkorning": False, "flöde_timeout": False, "tryck_ok": True, "flöde_ok": True}),
        # Pressure timeout after pump start
        (1, 0, 0, 1, 1, {"tryck_timeout": True, "oväntat_tryck": False, "torrkorning": False, "flöde_timeout": False, "tryck_ok": False, "flöde_ok": True}),
        # Unexpected pressure when pump off
        (2, 0, 1, 0, 0, {"tryck_timeout": False, "oväntat_tryck": True, "torrkorning": False, "flöde_timeout": False, "tryck_ok": True, "flöde_ok": False}),
        # Torrkörning: flow lost during operation
        (0, 2, 1, 0, 1, {"tryck_timeout": False, "oväntat_tryck": False, "torrkorning": True, "flöde_timeout": False, "tryck_ok": True, "flöde_ok": False}),
        # Flow initial timeout
        (0, 1, 1, 0, 1, {"tryck_timeout": False, "oväntat_tryck": False, "torrkorning": False, "flöde_timeout": True, "tryck_ok": True, "flöde_ok": False}),
    ],
)
def test_status_safety_flags(client, mock_modbus, pressure_alarm, flow_alarm, pressure_ok, flow_ok, pump_on, expected_flags):
    """Validate computed safety flags for digital sensors."""

    def _result(values):
        result = MagicMock()
        result.isError.return_value = False
        result.registers = values
        return result

    def _side_effect(address, count=1, unit=None):
        mapping = {
            MW_STATUS_ZONE: [0, pump_on, 0, 0],
            # MW54-56 maps to: [MW54=pressure_alarm, MW55=flow_switch, MW56=flow_alarm]
            MW_PRESSURE_ALARM: [pressure_alarm, flow_ok, flow_alarm],
            MW_HEARTBEAT: [0, 0, 0, 0],
            MW_MODE: [0],
            MW_MODE_OVERRIDE: [1],
            MW_PRESSURE_SWITCH: [pressure_ok],
            MW_BLOCK_REASON: [0],
        }
        values = mapping.get(address, [0] * count)
        if len(values) < count:
            values = values + [0] * (count - len(values))
        return _result(values[:count])

    mock_modbus.read_holding_registers.side_effect = _side_effect

    response = client.get("/status", headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    payload = response.json()

    assert payload["pressure_switch"] == (pressure_ok == 1)
    assert payload["pressure_alarm"] == pressure_alarm
    assert payload["flow_switch"] == (flow_ok == 1)
    assert payload["flow_alarm"] == flow_alarm
    for key, value in expected_flags.items():
        assert payload["safety"][key] is value


def test_status_modbus_failure_is_sanitized(client, caplog):
    """Ensure Modbus failures are logged while the user gets a generic error message"""
    error_result = MagicMock()
    error_result.isError.return_value = True
    error_result.registers = []

    with patch('api_main.mb_client') as mock:
        mock_client_instance = MagicMock()
        mock_client_instance.connect.return_value = True
        mock_client_instance.close.return_value = None
        mock_client_instance.read_holding_registers.return_value = error_result
        mock.return_value = mock_client_instance

        with caplog.at_level(logging.WARNING, logger=API_LOGGER_NAME):
            response = client.get("/status", headers={"X-API-Key": API_KEY})

    assert response.status_code == 502
    assert response.json()["detail"] == USER_MODBUS_ERROR
    assert any("read status registers MW50-53" in message for message in caplog.messages)


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


def test_set_mode_local(client, mock_modbus):
    """Test setting local mode (1)"""
    response = client.post(
        "/set-mode/1",
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["mode"] == 1
    assert "Lokalt läge" in data["mode_text"]


def test_set_mode_remote(client, mock_modbus):
    """Test setting remote mode (2)"""
    response = client.post(
        "/set-mode/2",
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["mode"] == 2
    assert "Fjärrläge" in data["mode_text"]


def test_set_mode_neutral(client, mock_modbus):
    """Test setting neutral mode (0)"""
    response = client.post(
        "/set-mode/0",
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["mode"] == 0
    assert "Neutral" in data["mode_text"]


def test_set_mode_invalid(client, mock_modbus):
    """Test setting invalid mode value"""
    response = client.post(
        "/set-mode/3",
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 400
    assert "mode must be" in response.json()["detail"]


def test_set_mode_unauthorized(client):
    """Test set mode without API key"""
    response = client.post("/set-mode/1")
    assert response.status_code == 401


def test_status_includes_mode(client, mock_modbus):
    """Test that status endpoint includes mode information"""
    response = client.get("/status", headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert "mode" in data
    assert "mode_text" in data


def test_rain_forecast_authorized(client):
    """Test rain forecast endpoint with valid API key"""
    with patch('api_main.requests.get') as mock_get:
        # Mock forecast response
        mock_forecast_response = MagicMock()
        mock_forecast_response.status_code = 200
        mock_forecast_response.json.return_value = {
            "hourly": {
                "time": ["2024-01-01T00:00", "2024-01-01T01:00", "2024-01-01T02:00"],
                "precipitation": [0.5, 1.0, 0.3]
            }
        }
        
        # Mock historical response
        mock_historical_response = MagicMock()
        mock_historical_response.status_code = 200
        mock_historical_response.json.return_value = {
            "daily": {
                "time": ["2024-01-01", "2024-01-02"],
                "precipitation_sum": [2.5, 1.2]
            }
        }
        
        mock_get.side_effect = [mock_forecast_response, mock_historical_response]
        
        response = client.get("/rain-forecast", headers={"X-API-Key": API_KEY})
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "forecast_24h" in data
        assert "history_7d" in data
        assert "location" in data
        assert "total_mm" in data["forecast_24h"]
        assert "hourly" in data["forecast_24h"]
        assert "daily" in data["history_7d"]


def test_rain_forecast_unauthorized(client):
    """Test rain forecast endpoint without API key"""
    response = client.get("/rain-forecast")
    assert response.status_code == 401


def test_rain_forecast_api_error(client):
    """Test rain forecast endpoint when weather API fails"""
    with patch('api_main.requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException("API unavailable")
        
        response = client.get("/rain-forecast", headers={"X-API-Key": API_KEY})
        assert response.status_code == 502


def test_process_view_authorized(client, mock_modbus):
    """Test process view endpoint with valid API key"""
    # Setup mock to return multiple register reads
    with patch('api_main.mb_client') as mock:
        mock_client_instance = MagicMock()
        mock_client_instance.connect.return_value = True
        mock_client_instance.close.return_value = None
        
        # Mock multiple read operations
        def mock_read(address, count, unit):
            result = MagicMock()
            result.isError.return_value = False
            
            if address == 50:  # MW_STATUS_ZONE
                result.registers = [2, 1, 5, 2]  # zone=2, pump=on, steg=5, selected=2
            elif address == 70:  # MW_HEARTBEAT
                result.registers = [1, 100, 0x04, 0]  # heartbeat, count, eventmask, block_reason
            elif address == 20:  # MW_TID_CENTER
                result.registers = [30, 15]  # tid_center, tid_horn
            elif address == 30:  # MW_MARKFUKT
                result.registers = [65, 2, 18]  # markfukt, regen24, temp
            elif address == 100:  # MW_MODE
                result.registers = [2]  # mode
            else:
                result.registers = [0] * count
            
            return result
        
        mock_client_instance.read_holding_registers.side_effect = mock_read
        mock.return_value = mock_client_instance
        
        response = client.get("/process-view", headers={"X-API-Key": API_KEY})
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "zones" in data
        assert len(data["zones"]) == 7
        assert "pump" in data
        assert data["pump"]["on"] is True
        assert "sequence" in data
        assert "errors" in data
        assert "block_status" in data
        assert "environment" in data
        assert "configuration" in data
        assert "mode" in data


def test_process_view_unauthorized(client):
    """Test process view endpoint without API key"""
    response = client.get("/process-view")
    assert response.status_code == 401


def test_zone_control_start_authorized(client, mock_modbus):
    """Test zone control endpoint to start a zone"""
    response = client.post(
        "/zone-control",
        json={"zone": 3, "action": "start"},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["action"] == "start"
    assert data["zone"] == 3
    assert "message" in data


def test_zone_control_stop_authorized(client, mock_modbus):
    """Test zone control endpoint to stop irrigation"""
    response = client.post(
        "/zone-control",
        json={"zone": 1, "action": "stop"},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["action"] == "stop"
    assert "message" in data


def test_zone_control_unauthorized(client):
    """Test zone control endpoint without API key"""
    response = client.post(
        "/zone-control",
        json={"zone": 1, "action": "start"}
    )
    assert response.status_code == 401


def test_zone_control_invalid_zone(client, mock_modbus):
    """Test zone control endpoint with invalid zone"""
    response = client.post(
        "/zone-control",
        json={"zone": 10, "action": "start"},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 400


def test_zone_control_invalid_action(client, mock_modbus):
    """Test zone control endpoint with invalid action"""
    response = client.post(
        "/zone-control",
        json={"zone": 1, "action": "invalid"},
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
