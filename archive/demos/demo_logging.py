#!/usr/bin/env python3
"""
Demonstration script to show enhanced logging functionality.
This script simulates user interactions and shows the resulting logs.
"""

import logging
import sys
import os
from io import StringIO

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock pymodbus before importing
from unittest.mock import MagicMock
sys.modules['pymodbus'] = MagicMock()
sys.modules['pymodbus.client'] = MagicMock()

from fastapi.testclient import TestClient
from api_main import app, API_KEY

# Setup logging to capture output
log_stream = StringIO()
handler = logging.StreamHandler(log_stream)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))

# Get the API logger
api_logger = logging.getLogger("bevattning.api")
api_logger.addHandler(handler)
api_logger.setLevel(logging.DEBUG)

# Create test client
client = TestClient(app)

print("=" * 80)
print("DEMONSTRATION: Enhanced Logging and Error Reporting")
print("=" * 80)
print()

# Mock the Modbus client
from unittest.mock import patch

mock_modbus_client = MagicMock()
mock_modbus_client.connect.return_value = True
mock_modbus_client.close.return_value = None

# Mock read registers
mock_read_result = MagicMock()
mock_read_result.isError.return_value = False
mock_read_result.registers = [1, 0, 0, 1, 0, 0, 0, 0]
mock_modbus_client.read_holding_registers.return_value = mock_read_result

# Mock write register
mock_write_result = MagicMock()
mock_write_result.isError.return_value = False
mock_modbus_client.write_register.return_value = mock_write_result

with patch('api_main.mb_client', return_value=mock_modbus_client):
    
    # Scenario 1: Start zone via zone-control
    print("SCENARIO 1: User starts Zone 3 via Process View")
    print("-" * 80)
    log_stream.truncate(0)
    log_stream.seek(0)
    
    response = client.post(
        "/zone-control",
        json={"zone": 3, "action": "start"},
        headers={"X-API-Key": API_KEY}
    )
    
    print(f"Response: {response.json()}")
    print("\nLogs generated:")
    print(log_stream.getvalue())
    print()
    
    # Scenario 2: Stop via zone-control
    print("SCENARIO 2: User stops irrigation via Process View")
    print("-" * 80)
    log_stream.truncate(0)
    log_stream.seek(0)
    
    response = client.post(
        "/zone-control",
        json={"zone": 3, "action": "stop"},
        headers={"X-API-Key": API_KEY}
    )
    
    print(f"Response: {response.json()}")
    print("\nLogs generated:")
    print(log_stream.getvalue())
    print()
    
    # Scenario 3: Manual command
    print("SCENARIO 3: User starts manual irrigation for Zone 5")
    print("-" * 80)
    log_stream.truncate(0)
    log_stream.seek(0)
    
    response = client.post(
        "/command/manual",
        json={"zone": 5},
        headers={"X-API-Key": API_KEY}
    )
    
    print(f"Response: {response.json()}")
    print("\nLogs generated:")
    print(log_stream.getvalue())
    print()
    
    # Scenario 4: Auto-start
    print("SCENARIO 4: User starts auto-program")
    print("-" * 80)
    log_stream.truncate(0)
    log_stream.seek(0)
    
    response = client.post(
        "/command/start-auto",
        headers={"X-API-Key": API_KEY}
    )
    
    print(f"Response: {response.json()}")
    print("\nLogs generated:")
    print(log_stream.getvalue())
    print()
    
    # Scenario 5: Process view call
    print("SCENARIO 5: Process View fetches system status")
    print("-" * 80)
    log_stream.truncate(0)
    log_stream.seek(0)
    
    # Need to mock multiple reads for process-view
    def mock_read_process_view(address, count, unit):
        result = MagicMock()
        result.isError.return_value = False
        
        if address == 50:  # Status registers
            result.registers = [2, 1, 3, 2]
        elif address == 70:  # Heartbeat registers
            result.registers = [1, 100, 4, 0]
        elif address == 20:  # Config
            result.registers = [30, 15]
        elif address == 30:  # Environment
            result.registers = [45, 2, 18]
        elif address == 34:  # Thresholds
            result.registers = [5, 80]
        elif address == 100:  # Mode
            result.registers = [2]
        else:
            result.registers = [0] * count
        
        return result
    
    mock_modbus_client.read_holding_registers.side_effect = mock_read_process_view
    
    response = client.get(
        "/process-view",
        headers={"X-API-Key": API_KEY}
    )
    
    print(f"Response status: {response.status_code}")
    data = response.json()
    print(f"Active errors: {[k for k, v in data['error_details'].items() if v['active']]}")
    print(f"Block status: {data['block_status']['text']}")
    print("\nLogs generated:")
    print(log_stream.getvalue())
    print()

print("=" * 80)
print("LOGGING TAG SUMMARY")
print("=" * 80)
print("""
Structured logging tags used:

1. [USER_ACTION] - All user-initiated actions (start, stop, manual, auto)
   - Includes timestamp for audit trail
   - Logged at INFO level

2. [ZONE_EVENT] - Zone-specific events (zone started, zone stopped)
   - Tracks which zone and what action
   - Logged at INFO level

3. [PUMP_EVENT] - Pump control events (pump started, pump stopped)
   - Critical for water hammer prevention tracking
   - Logged at INFO level

4. [API_CALL] - API endpoint access
   - Tracks which endpoints are being called
   - Logged at DEBUG level

5. [DASH_USER_ACTION] - Dash frontend user interactions
   - Button clicks, zone clicks
   - Logged at INFO level

6. [DASH_API_CALL] - Dash to API communication
   - Logged at INFO level

7. [DASH_API_SUCCESS] / [DASH_API_ERROR] - API call results
   - Logged at INFO/ERROR level

These structured tags enable easy filtering and monitoring of:
- User actions for audit purposes
- System events for troubleshooting
- API performance and errors
- Frontend interactions
""")

print("=" * 80)
print("ERROR REPORTING IMPROVEMENTS")
print("=" * 80)
print("""
Enhanced error visibility:

1. Critical Error Banner
   - Prominent red banner for E-stop and critical errors
   - Appears at top of Process View when active
   - Includes clear explanation of the error

2. Detailed Error Explanations
   - Each error type includes:
     * Active status (boolean)
     * Human-readable text
     * Detailed explanation with current values
     * Severity level (critical/warning/info)

3. Zone Highlighting
   - Zones affected by errors have red border
   - Size and color indicate zone status
   - Hover text shows zone status details

4. Color-Coded Severity
   - Critical (red): E-stop, system failures
   - Warning (orange): Moisture/rain blocks
   - Info (blue): Normal operations, sequence active

5. Real-time Updates
   - Error status updates every 5 seconds
   - Immediate feedback on user actions
   - Block reasons with explanations
""")
print()
