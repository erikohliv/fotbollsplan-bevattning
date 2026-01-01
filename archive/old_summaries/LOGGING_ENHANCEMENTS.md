# Enhanced Logging and Error Reporting

This document describes the enhanced logging and error reporting features implemented for the irrigation system.

## Overview

The system now includes comprehensive event logging and improved error visibility to facilitate troubleshooting and provide better user feedback.

## Structured Logging Tags

All log entries use structured tags for easy filtering and monitoring:

### Backend (FastAPI) Tags

1. **[USER_ACTION]** - User-initiated actions
   - Auto-program start/stop
   - Manual zone control
   - Night program activation
   - Configuration changes
   - Includes timestamp for audit trail
   - Logged at INFO level

2. **[ZONE_EVENT]** - Zone-specific operations
   - Zone start/stop events
   - Zone selection changes
   - Includes zone number and action
   - Logged at INFO level

3. **[PUMP_EVENT]** - Pump control operations
   - Pump start/stop events
   - Critical for tracking anti-water hammer operations
   - Logged at INFO level

4. **[API_CALL]** - API endpoint access
   - Tracks endpoint usage
   - Logged at DEBUG level
   - Includes timestamp

### Frontend (Dash) Tags

5. **[DASH_USER_ACTION]** - Frontend user interactions
   - Button clicks (start zone, stop)
   - Zone clicks in graphical view
   - Dropdown selections
   - Logged at INFO level

6. **[DASH_API_CALL]** - Dash-to-API communication
   - Tracks all API requests from frontend
   - Includes endpoint and method
   - Logged at INFO level

7. **[DASH_API_SUCCESS]** / **[DASH_API_ERROR]** - API call results
   - Success/failure status of API calls
   - Logged at INFO/ERROR level

## Log Examples

### Zone Start via Process View
```
2025-12-18 20:12:40 INFO: [USER_ACTION] zone-control anropad - zon=3 action=start timestamp=1766088760
2025-12-18 20:12:40 INFO: [ZONE_EVENT] Zon 3 STARTAS via process view
2025-12-18 20:12:40 INFO: [ZONE_EVENT] Zon 3 STARTAD - använder auto-tider
```

### Manual Irrigation
```
2025-12-18 20:12:40 INFO: [USER_ACTION] Manuell körning initieras - zon=5 timestamp=1766088760
2025-12-18 20:12:40 INFO: [USER_ACTION] Manuell körning startad - zon=5
```

### Stop Command
```
2025-12-18 20:12:40 INFO: [USER_ACTION] Stopp-kommando mottaget - timestamp=1766088760
2025-12-18 20:12:40 INFO: [PUMP_EVENT] Bevattning STOPPAD via process view
```

### Dash Frontend Interaction
```
2025-12-18 20:15:30 INFO: [DASH_USER_ACTION] Knapp 'Starta Zon' klickad - zon=2
2025-12-18 20:15:30 INFO: [DASH_API_CALL] POST /zone-control - data={'zone': 2, 'action': 'start'}
2025-12-18 20:15:30 INFO: [DASH_API_SUCCESS] POST /zone-control - status=200
2025-12-18 20:15:30 INFO: [DASH_USER_ACTION] Zon 2 startad via knapp-kontroll
```

## Enhanced Error Reporting

### Process View Endpoint (`/process-view`)

The `/process-view` endpoint now includes comprehensive error information:

```json
{
  "ok": true,
  "error_details": {
    "e_stop": {
      "active": false,
      "text": "E-stop aktiv",
      "explanation": "Nödstoppet är aktiverat. Kontrollera fysisk nödstopp-knapp...",
      "severity": "critical"
    },
    "moisture_block": {
      "active": false,
      "text": "Markfukt-block",
      "explanation": "Markfukten (45%) är över tröskelvärdet (80%)...",
      "severity": "warning"
    },
    "rain_block": {
      "active": false,
      "text": "Regn-block",
      "explanation": "Nederbörd senaste 24h (2 mm) är över tröskelvärdet (5 mm)...",
      "severity": "warning"
    }
  },
  "block_status": {
    "code": 0,
    "text": "OK",
    "explanation": "Systemet fungerar normalt. Inga aktiva blockeringar.",
    "blocked": false
  }
}
```

### Error Severity Levels

- **critical** (red) - E-stop, system failures requiring immediate attention
- **warning** (orange) - Moisture/rain blocks, anti-collision
- **info** (blue) - Normal operations, sequence active

### Frontend Error Display

#### 1. Critical Error Banner
- Appears at top of Process View when critical errors occur
- Red background with white text
- Large font for visibility
- Includes error explanation
- Persists until error is cleared

Example:
```
🚨 NÖDSTOPP AKTIVT
Nödstoppet är aktiverat. Kontrollera fysisk nödstopp-knapp och systemstatus.
```

#### 2. Error Status Panel
- Shows all active errors with color coding
- Grouped by severity (critical first)
- Includes:
  - Error icon and name
  - Detailed explanation
  - Current sensor values (for threshold-based errors)
  - Recommended actions

#### 3. Zone Highlighting
- Zones affected by errors show red border
- Border width increases for severity
- Hover text explains the error
- Visual feedback on zone status changes

#### 4. System Status Section
- "Systemstatus & Fel" panel on left side
- Real-time error updates (5-second refresh)
- Color-coded error boxes
- Expandable explanations

## Filtering and Monitoring Logs

### Filter by Tag
```bash
# Show all user actions
tail -f /var/log/bevattning.log | grep "\[USER_ACTION\]"

# Show zone events
tail -f /var/log/bevattning.log | grep "\[ZONE_EVENT\]"

# Show pump events (critical for anti-water hammer tracking)
tail -f /var/log/bevattning.log | grep "\[PUMP_EVENT\]"

# Show API errors
tail -f /var/log/bevattning.log | grep "\[DASH_API_ERROR\]"
```

### Filter by Zone
```bash
# Show all events for Zone 3
tail -f /var/log/bevattning.log | grep "zon=3"
```

### Audit Trail
```bash
# Show all user actions with timestamps
grep "\[USER_ACTION\]" /var/log/bevattning.log | grep "timestamp="
```

## Benefits

### 1. Improved Troubleshooting
- Structured tags allow quick filtering of relevant events
- Timestamps enable correlation of events
- Zone and action details in every log entry
- API success/failure tracking

### 2. Audit Trail
- All user actions logged with timestamps
- Zone start/stop events tracked
- Pump operations recorded
- Frontend interactions captured

### 3. Enhanced User Experience
- Immediate error feedback
- Clear error explanations
- Visual indicators (colors, icons, borders)
- Context-aware error messages with current values

### 4. Monitoring and Alerting
- Easy to set up log monitoring tools
- Structured format enables automated alerting
- Critical errors clearly tagged
- API performance tracking

## Testing

Run the comprehensive test suite:
```bash
source .venv/bin/activate
pytest test_logging_enhancements.py -v
```

Run the demonstration script:
```bash
source .venv/bin/activate
python3 demo_logging.py
```

## Implementation Details

### Backend Changes
- Added structured logging tags to all user-facing endpoints
- Enhanced `/process-view` with detailed error information
- Added timestamp tracking for audit purposes
- Improved error explanations with current sensor values

### Frontend Changes
- Added logging to all user interaction callbacks
- Implemented critical error banner component
- Enhanced zone figure with error highlighting
- Added API call success/failure tracking
- Improved error status display with color coding

## Future Enhancements

Potential improvements for future versions:

1. **Log Aggregation**
   - Send logs to centralized logging service
   - Real-time log dashboard
   - Historical log analysis

2. **Alert System**
   - Email/SMS alerts for critical errors
   - Configurable alert thresholds
   - Alert suppression during maintenance

3. **Metrics Dashboard**
   - Zone usage statistics
   - Error frequency tracking
   - API performance metrics
   - User action heatmap

4. **Advanced Filtering**
   - Web-based log viewer
   - Time-range filtering
   - Multi-tag filtering
   - Export to CSV/JSON
