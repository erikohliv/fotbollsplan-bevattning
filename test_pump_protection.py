#!/usr/bin/env python3
"""
Test suite for pump_protection.py
"""

import pytest
import time
from pump_protection import (
    PumpState,
    check_pump_safety,
    get_diagnostics,
    START_GRACE_PERIOD,
    SLANGBROTT_DELAY,
    TORRKORNING_DELAY
)


class TestPumpState:
    """Test PumpState class"""
    
    def test_initialization(self):
        """Test that PumpState initializes correctly"""
        state = PumpState()
        assert state.time_running == 0.0
        assert state.timer_slangbrott == 0.0
        assert state.timer_torrkorning == 0.0
        assert state.last_check is None
        assert state.pump_was_active is False
        assert state.start_count == 0
        assert state.start_history == []
    
    def test_update_pump_start(self):
        """Test pump start detection"""
        state = PumpState()
        
        # Pump starts
        state.update(pump_active=True, delta_time=1.0)
        
        assert state.pump_was_active is True
        assert state.time_running == 1.0
        assert state.start_count == 1
        assert len(state.start_history) == 1
    
    def test_update_pump_running(self):
        """Test pump running time accumulation"""
        state = PumpState()
        
        # Pump starts
        state.update(pump_active=True, delta_time=1.0)
        # Pump continues running
        state.update(pump_active=True, delta_time=2.0)
        state.update(pump_active=True, delta_time=3.0)
        
        assert state.time_running == 6.0  # 1 + 2 + 3
        assert state.start_count == 1  # Only one start
    
    def test_update_pump_stop(self):
        """Test pump stop resets timers"""
        state = PumpState()
        
        # Pump starts and runs
        state.update(pump_active=True, delta_time=10.0)
        state.timer_slangbrott = 5.0
        state.timer_torrkorning = 3.0
        
        # Pump stops
        state.update(pump_active=False, delta_time=1.0)
        
        assert state.pump_was_active is False
        assert state.time_running == 0.0
        assert state.timer_slangbrott == 0.0
        assert state.timer_torrkorning == 0.0
    
    def test_reset(self):
        """Test state reset"""
        state = PumpState()
        
        # Set some values
        state.update(pump_active=True, delta_time=10.0)
        state.start_count = 5
        state.timer_slangbrott = 3.0
        
        # Reset
        state.reset()
        
        assert state.time_running == 0.0
        assert state.start_count == 0
        assert state.timer_slangbrott == 0.0


class TestCheckPumpSafety:
    """Test check_pump_safety function"""
    
    def test_pump_off_returns_ok(self):
        """Test that pump off always returns OK"""
        state = PumpState()
        
        result = check_pump_safety(
            state=state,
            pump_active=False,
            flow_detected=False,
            pressure_ok=False,
            delta_time=1.0
        )
        
        assert result == "OK"
    
    def test_grace_period_returns_ok(self):
        """Test that grace period masks alarms"""
        state = PumpState()
        
        # Simulate conditions that would trigger alarm outside grace period
        for i in range(10):
            result = check_pump_safety(
                state=state,
                pump_active=True,
                flow_detected=False,
                pressure_ok=False,
                delta_time=2.0
            )
            
            if state.time_running < START_GRACE_PERIOD:
                assert result == "OK", f"Should be OK during grace period at {state.time_running}s"
    
    def test_normal_operation(self):
        """Test normal operation (flow=yes, pressure=yes)"""
        state = PumpState()
        
        # Run through grace period
        state.update(pump_active=True, delta_time=START_GRACE_PERIOD + 1)
        
        # Normal operation
        result = check_pump_safety(
            state=state,
            pump_active=True,
            flow_detected=True,
            pressure_ok=True,
            delta_time=5.0
        )
        
        assert result == "OK"
        assert state.timer_slangbrott == 0.0
        assert state.timer_torrkorning == 0.0
    
    def test_slangbrott_detection(self):
        """Test hose break detection (flow=yes, pressure=no)"""
        state = PumpState()
        
        # Run through grace period
        state.update(pump_active=True, delta_time=START_GRACE_PERIOD + 1)
        
        # Simulate hose break - should build up timer
        for i in range(int(SLANGBROTT_DELAY) + 2):
            result = check_pump_safety(
                state=state,
                pump_active=True,
                flow_detected=True,
                pressure_ok=False,
                delta_time=1.0
            )
        
        assert result == "ALARM_SLANGBROTT"
        assert state.timer_slangbrott > SLANGBROTT_DELAY
    
    def test_slangbrott_warning_before_alarm(self):
        """Test that slangbrott shows warning before alarm"""
        state = PumpState()
        
        # Run through grace period
        state.update(pump_active=True, delta_time=START_GRACE_PERIOD + 1)
        
        # Simulate hose break but not long enough for alarm
        result = check_pump_safety(
            state=state,
            pump_active=True,
            flow_detected=True,
            pressure_ok=False,
            delta_time=SLANGBROTT_DELAY - 0.5
        )
        
        assert result == "OK"  # Not enough time yet
        assert state.timer_slangbrott < SLANGBROTT_DELAY
    
    def test_torrkorning_detection(self):
        """Test dry run detection (flow=no, pressure=no)"""
        state = PumpState()
        
        # Run through grace period
        state.update(pump_active=True, delta_time=START_GRACE_PERIOD + 1)
        
        # Simulate dry run
        for i in range(int(TORRKORNING_DELAY) + 2):
            result = check_pump_safety(
                state=state,
                pump_active=True,
                flow_detected=False,
                pressure_ok=False,
                delta_time=1.0
            )
        
        assert result == "ALARM_TORRKORNING"
        assert state.timer_torrkorning > TORRKORNING_DELAY
    
    def test_slangvinda_normal_stop(self):
        """Test normal stop from hose reel (flow=no, pressure=yes)"""
        state = PumpState()
        
        # Run through grace period
        state.update(pump_active=True, delta_time=START_GRACE_PERIOD + 1)
        
        # Simulate hose reel closed
        result = check_pump_safety(
            state=state,
            pump_active=True,
            flow_detected=False,
            pressure_ok=True,
            delta_time=1.0
        )
        
        assert result == "STOP_NORMAL"
    
    def test_alarm_timer_resets_on_recovery(self):
        """Test that alarm timers reset when condition improves"""
        state = PumpState()
        
        # Run through grace period
        state.update(pump_active=True, delta_time=START_GRACE_PERIOD + 1)
        
        # Start building up slangbrott timer
        check_pump_safety(
            state=state,
            pump_active=True,
            flow_detected=True,
            pressure_ok=False,
            delta_time=1.0
        )
        
        assert state.timer_slangbrott > 0
        
        # Condition improves - back to normal
        result = check_pump_safety(
            state=state,
            pump_active=True,
            flow_detected=True,
            pressure_ok=True,
            delta_time=1.0
        )
        
        assert result == "OK"
        assert state.timer_slangbrott == 0.0


class TestGetDiagnostics:
    """Test get_diagnostics function"""
    
    def test_diagnostics_format(self):
        """Test that diagnostics returns expected format"""
        state = PumpState()
        state.time_running = 30.5
        state.timer_slangbrott = 1.5
        state.timer_torrkorning = 0.0
        state.start_count = 2
        
        diag = get_diagnostics(
            state=state,
            pump_active=True,
            flow_detected=True,
            pressure_ok=False
        )
        
        assert "pump_active" in diag
        assert "flow_detected" in diag
        assert "pressure_ok" in diag
        assert "time_running" in diag
        assert "timer_slangbrott" in diag
        assert "timer_torrkorning" in diag
        assert "start_count" in diag
        assert "timestamp" in diag
        
        assert diag["pump_active"] is True
        assert diag["flow_detected"] is True
        assert diag["pressure_ok"] is False
        assert diag["time_running"] == 30.5
        assert diag["timer_slangbrott"] == 1.5
        assert diag["start_count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
