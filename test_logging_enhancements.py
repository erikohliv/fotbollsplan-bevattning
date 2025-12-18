#!/usr/bin/env python3
"""
Test suite for enhanced logging and error reporting functionality.
Tests both FastAPI backend logging and Dash frontend error visibility.
"""

import pytest
import logging
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

from api_main import app, API_KEY, API_LOGGER_NAME


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
                result.registers = [1, 100, 4, 0]  # heartbeat, count, eventmask, block_reason=0
            # MW20-21: Config
            elif address == 20:
                result.registers = [30, 15]  # tid_center=30, tid_horn=15
            # MW30-32: Environment
            elif address == 30:
                result.registers = [45, 2, 18]  # moisture=45%, rain=2mm, temp=18C
            # MW34-35: Thresholds
            elif address == 34:
                result.registers = [5, 80]  # rain_threshold=5mm, moisture_threshold=80%
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


class TestFastAPILogging:
    """Test suite for FastAPI backend logging"""
    
    def test_zone_control_start_logging(self, client, mock_modbus, caplog):
        """Test that zone control start action is logged with correct tags"""
        with caplog.at_level(logging.INFO, logger=API_LOGGER_NAME):
            response = client.post(
                "/zone-control",
                json={"zone": 3, "action": "start"},
                headers={"X-API-Key": API_KEY}
            )
        
        assert response.status_code == 200
        
        # Check for USER_ACTION and ZONE_EVENT log tags
        logs = [record.message for record in caplog.records]
        assert any("[USER_ACTION]" in log and "zone-control" in log for log in logs)
        assert any("[ZONE_EVENT]" in log and "STARTAS" in log for log in logs)
        assert any("[ZONE_EVENT]" in log and "STARTAD" in log for log in logs)
    
    def test_zone_control_stop_logging(self, client, mock_modbus, caplog):
        """Test that zone control stop action is logged with correct tags"""
        with caplog.at_level(logging.INFO, logger=API_LOGGER_NAME):
            response = client.post(
                "/zone-control",
                json={"zone": 5, "action": "stop"},
                headers={"X-API-Key": API_KEY}
            )
        
        assert response.status_code == 200
        
        # Check for PUMP_EVENT log tags
        logs = [record.message for record in caplog.records]
        assert any("[PUMP_EVENT]" in log and "STOPP-kommando" in log for log in logs)
        assert any("[PUMP_EVENT]" in log and "STOPPAD" in log for log in logs)
    
    def test_manual_command_logging(self, client, mock_modbus, caplog):
        """Test that manual command is logged with zone information"""
        with caplog.at_level(logging.INFO, logger=API_LOGGER_NAME):
            response = client.post(
                "/command/manual",
                json={"zone": 4},
                headers={"X-API-Key": API_KEY}
            )
        
        assert response.status_code == 200
        
        # Check for USER_ACTION logs with zone number
        logs = [record.message for record in caplog.records]
        assert any("[USER_ACTION]" in log and "Manuell körning" in log and "zon=4" in log 
                   for log in logs)
        assert any("[USER_ACTION]" in log and "startad" in log for log in logs)
    
    def test_start_auto_logging(self, client, mock_modbus, caplog):
        """Test that auto-start command is logged"""
        with caplog.at_level(logging.INFO, logger=API_LOGGER_NAME):
            response = client.post(
                "/command/start-auto",
                headers={"X-API-Key": API_KEY}
            )
        
        assert response.status_code == 200
        
        # Check for USER_ACTION logs
        logs = [record.message for record in caplog.records]
        assert any("[USER_ACTION]" in log and "Auto-program" in log for log in logs)
    
    def test_start_night_program_logging(self, client, mock_modbus, caplog):
        """Test that night program start is logged"""
        with caplog.at_level(logging.INFO, logger=API_LOGGER_NAME):
            response = client.post(
                "/command/start-night-program",
                headers={"X-API-Key": API_KEY}
            )
        
        assert response.status_code == 200
        
        # Check for USER_ACTION logs
        logs = [record.message for record in caplog.records]
        assert any("[USER_ACTION]" in log and "Natt-program" in log for log in logs)
    
    def test_stop_command_logging(self, client, mock_modbus, caplog):
        """Test that stop command is logged"""
        with caplog.at_level(logging.INFO, logger=API_LOGGER_NAME):
            response = client.post(
                "/command/stop",
                headers={"X-API-Key": API_KEY}
            )
        
        assert response.status_code == 200
        
        # Check for USER_ACTION logs
        logs = [record.message for record in caplog.records]
        assert any("[USER_ACTION]" in log and "Stopp-kommando" in log for log in logs)
        assert any("verkställt" in log for log in logs)
    
    def test_process_view_logging(self, client, mock_modbus, caplog):
        """Test that process view API call is logged"""
        with caplog.at_level(logging.DEBUG, logger=API_LOGGER_NAME):
            response = client.get(
                "/process-view",
                headers={"X-API-Key": API_KEY}
            )
        
        assert response.status_code == 200
        
        # Check for API_CALL log
        logs = [record.message for record in caplog.records]
        assert any("[API_CALL]" in log and "/process-view" in log for log in logs)
    
    def test_logging_includes_timestamp(self, client, mock_modbus, caplog):
        """Test that user action logs include timestamp"""
        with caplog.at_level(logging.INFO, logger=API_LOGGER_NAME):
            response = client.post(
                "/zone-control",
                json={"zone": 2, "action": "start"},
                headers={"X-API-Key": API_KEY}
            )
        
        assert response.status_code == 200
        
        # Check that timestamp is included in logs
        logs = [record.message for record in caplog.records]
        assert any("timestamp=" in log for log in logs)


class TestProcessViewErrorDetails:
    """Test suite for process view error reporting"""
    
    def test_process_view_includes_error_details(self, client, mock_modbus):
        """Test that process view includes detailed error information"""
        response = client.get("/process-view", headers={"X-API-Key": API_KEY})
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that error_details exist
        assert 'error_details' in data
        assert isinstance(data['error_details'], dict)
        
        # Check that all error types are present
        error_types = ['e_stop', 'moisture_block', 'rain_block', 'anti_collision', 'sequence_active']
        for error_type in error_types:
            assert error_type in data['error_details']
            assert 'active' in data['error_details'][error_type]
            assert 'text' in data['error_details'][error_type]
            assert 'explanation' in data['error_details'][error_type]
            assert 'severity' in data['error_details'][error_type]
    
    def test_process_view_includes_block_status(self, client, mock_modbus):
        """Test that process view includes block status with explanations"""
        response = client.get("/process-view", headers={"X-API-Key": API_KEY})
        
        assert response.status_code == 200
        data = response.json()
        
        # Check block_status structure
        assert 'block_status' in data
        block_status = data['block_status']
        assert 'code' in block_status
        assert 'text' in block_status
        assert 'explanation' in block_status
        assert 'blocked' in block_status
        
        # Block reason 0 should be OK and not blocked
        assert block_status['code'] == 0
        assert block_status['blocked'] == False
        assert 'OK' in block_status['text']
    
    def test_process_view_error_severity_levels(self, client):
        """Test that error details include correct severity levels"""
        # Mock with E-stop active (critical)
        with patch('api_main.mb_client') as mock:
            mock_client_instance = MagicMock()
            mock_client_instance.connect.return_value = True
            mock_client_instance.close.return_value = None
            
            def mock_read_with_estop(address, count, unit):
                result = MagicMock()
                result.isError.return_value = False
                
                if address == 50:
                    result.registers = [0, 0, 0, 0]
                elif address == 70:
                    result.registers = [1, 100, 1, 4]  # eventmask bit0=E-stop, block_reason=4
                elif address == 20:
                    result.registers = [30, 15]
                elif address == 30:
                    result.registers = [45, 2, 18]
                elif address == 34:
                    result.registers = [5, 80]
                elif address == 100:
                    result.registers = [2]
                else:
                    result.registers = [0] * count
                
                return result
            
            mock_client_instance.read_holding_registers.side_effect = mock_read_with_estop
            mock_write_result = MagicMock()
            mock_write_result.isError.return_value = False
            mock_client_instance.write_register.return_value = mock_write_result
            mock.return_value = mock_client_instance
            
            response = client.get("/process-view", headers={"X-API-Key": API_KEY})
            
            assert response.status_code == 200
            data = response.json()
            
            # E-stop should be critical severity
            assert data['error_details']['e_stop']['active'] == True
            assert data['error_details']['e_stop']['severity'] == 'critical'


class TestDashErrorVisibility:
    """Test suite for Dash frontend error visibility - structural tests"""
    
    def test_critical_error_banner_exists_in_layout(self):
        """Test that critical error banner div exists in Dash layout"""
        from dash_app import app as dash_app
        
        # The layout should include a div with id 'critical-error-banner'
        layout_str = str(dash_app.layout)
        assert 'critical-error-banner' in layout_str
    
    def test_zone_figure_supports_error_highlighting(self):
        """Test that zone figure function can handle error highlighting"""
        from dash_app import create_zone_figure
        
        # Create zone data with error_affected flag
        zones_data = []
        for i in range(1, 8):
            zones_data.append({
                'zone': i,
                'active': i == 2,
                'selected': i == 2,
                'error_affected': i == 2  # Mark zone 2 as affected by error
            })
        
        fig = create_zone_figure(zones_data)
        
        # Verify figure was created
        assert fig is not None
        assert len(fig.data) == 7  # 7 zones
    
    def test_make_api_request_logs_calls(self):
        """Test that make_api_request logs all calls"""
        from dash_app import make_api_request
        import logging
        
        with patch('dash_app.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"ok": True}
            mock_get.return_value = mock_response
            
            with patch('dash_app.logger') as mock_logger:
                result = make_api_request("/test-endpoint", method="GET")
                
                # Verify logging calls were made
                assert mock_logger.info.called
                # Check for DASH_API_CALL and DASH_API_SUCCESS logs
                call_args = [str(call) for call in mock_logger.info.call_args_list]
                assert any("DASH_API_CALL" in str(call) for call in call_args)
                assert any("DASH_API_SUCCESS" in str(call) for call in call_args)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
