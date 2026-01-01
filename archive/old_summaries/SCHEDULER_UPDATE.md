# Auto-Watering Schedule Update - Implementation Summary

## Overview
This update changes the auto-watering schedule from 02:00 to 01:00 daily, adding robust conditional checks before watering execution.

## What Changed

### 1. New Scheduler Module (`bevattning_scheduler.py`)
A new Python scheduler that:
- Runs daily at 01:00 (default, configurable via `--schedule-hour` and `--schedule-minute`)
- Checks BlockReason (MW73 Modbus register) before auto-watering
- Blocks watering if unsafe conditions are detected:
  - BlockReason=1: Rain exceeds threshold
  - BlockReason=2: Soil moisture exceeds threshold
  - BlockReason=3: Anti-collision/pump busy
  - BlockReason=4: E-stop active
- Integrates with existing `bevattning_controller.py` logic

### 2. Controller Updates (`bevattning_controller.py`)
- Added `MW_BLOCK_REASON = 73` constant for BlockReason register
- Fixed argparse help strings to avoid format string issues

### 3. System Integration Files

#### Systemd Timer (Recommended)
- `systemd_bevattning-scheduler.timer`: Triggers daily at 01:00
- `systemd_bevattning-scheduler.service`: Executes scheduler

Installation:
```bash
sudo cp systemd_bevattning-scheduler.timer /etc/systemd/system/
sudo cp systemd_bevattning-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bevattning-scheduler.timer
sudo systemctl start bevattning-scheduler.timer
```

#### Cron Alternative
- `crontab.example`: Example cron configuration

Installation:
```bash
crontab -e
# Add: 0 1 * * * /path/to/venv/bin/python3 /path/to/bevattning_scheduler.py --run-now --auto-start
```

### 4. Testing
- `test_bevattning_scheduler.py`: 9 comprehensive unit tests
  - Schedule time calculation (same day and next day)
  - Block condition detection for all BlockReason values
  - Watering execution and blocking logic
- All tests passing ✓

### 5. Documentation
- Updated `README.md` with installation and usage instructions
- Added `.gitignore` to exclude Python cache and temporary files

## Usage Examples

### Run Immediately (for testing)
```bash
python3 bevattning_scheduler.py --run-now --auto-start
```

### Run Once at Next Scheduled Time
```bash
python3 bevattning_scheduler.py --once --auto-start
```

### Continuous Scheduler Mode
```bash
python3 bevattning_scheduler.py --auto-start
```

### Custom Schedule Time
```bash
python3 bevattning_scheduler.py --schedule-hour 2 --schedule-minute 30 --auto-start
```

### Dry Run (No Modbus Writes)
```bash
python3 bevattning_scheduler.py --run-now --dry-run --simulate
```

## Safety Features

1. **Block Condition Checks**: Before every auto-watering execution, the scheduler reads MW73 (BlockReason) from the PLC
2. **Conditional Execution**: Watering only proceeds if BlockReason=0 (no blocks)
3. **Weather Integration**: Existing weather and soil moisture checks from `bevattning_controller.py` still apply
4. **Logging**: All executions and block conditions are logged

## Testing Performed

✅ Unit tests (9 tests, all passing)
✅ Integration tests (scheduler execution, systemd config, cron config)
✅ Code review completed
✅ Security scan (CodeQL) - no issues found
✅ Dry-run simulation verified
✅ Help/usage documentation validated

## Migration Notes

If you were previously using a manual cron job or systemd timer set to 02:00:
1. Remove the old 02:00 configuration
2. Install the new 01:00 scheduler using the instructions above
3. The new scheduler provides the same functionality plus additional safety checks

## Support

For issues or questions, refer to:
- `README.md`: Installation and usage instructions
- `test_bevattning_scheduler.py`: Examples of expected behavior
- Repository issues: https://github.com/erikohliv/fotbollsplan-bevattning/issues
