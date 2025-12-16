#!/usr/bin/env python3
"""
Test script for bevattning_scheduler.py
Tests the scheduling logic and block condition checks
"""
import unittest
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bevattning_scheduler


class TestBevattningScheduler(unittest.TestCase):
    """Test cases for bevattning_scheduler"""
    
    def test_wait_until_next_schedule_same_day(self):
        """Test scheduling for later today"""
        # Mock datetime to be 00:30
        with patch('bevattning_scheduler.datetime') as mock_datetime:
            mock_now = datetime(2025, 12, 16, 0, 30, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            # Schedule is at 01:00, should wait 30 minutes
            wait_seconds = bevattning_scheduler.wait_until_next_schedule(hour=1, minute=0)
            
            # Should be approximately 30 minutes (1800 seconds)
            self.assertAlmostEqual(wait_seconds, 1800, delta=1)
    
    def test_wait_until_next_schedule_next_day(self):
        """Test scheduling for tomorrow if time has passed"""
        # Mock datetime to be 02:00 (after 01:00 schedule)
        with patch('bevattning_scheduler.datetime') as mock_datetime:
            mock_now = datetime(2025, 12, 16, 2, 0, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            # Schedule is at 01:00, should wait until tomorrow
            wait_seconds = bevattning_scheduler.wait_until_next_schedule(hour=1, minute=0)
            
            # Should be approximately 23 hours (82800 seconds)
            self.assertAlmostEqual(wait_seconds, 82800, delta=1)
    
    def test_check_block_conditions_no_block(self):
        """Test that no block is returned when BlockReason is 0"""
        args = MagicMock()
        args.host = "127.0.0.1"
        args.port = 502
        args.unit = 1
        
        # Mock Modbus client to return BlockReason = 0 (no block)
        with patch('bevattning_scheduler.bevattning_controller.ModbusTcpClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = True
            
            mock_result = MagicMock()
            mock_result.registers = [0]  # BlockReason = 0
            mock_client.read_holding_registers.return_value = mock_result
            
            with patch('bevattning_scheduler.bevattning_controller.open_modbus_client', return_value=mock_client):
                should_block, reason = bevattning_scheduler.check_block_conditions(args)
                
                self.assertFalse(should_block)
                self.assertIsNone(reason)
    
    def test_check_block_conditions_rain_block(self):
        """Test that rain block is detected (BlockReason = 1)"""
        args = MagicMock()
        args.host = "127.0.0.1"
        args.port = 502
        args.unit = 1
        
        # Mock Modbus client to return BlockReason = 1 (rain)
        with patch('bevattning_scheduler.bevattning_controller.ModbusTcpClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = True
            
            mock_result = MagicMock()
            mock_result.registers = [1]  # BlockReason = 1 (rain)
            mock_client.read_holding_registers.return_value = mock_result
            
            with patch('bevattning_scheduler.bevattning_controller.open_modbus_client', return_value=mock_client):
                should_block, reason = bevattning_scheduler.check_block_conditions(args)
                
                self.assertTrue(should_block)
                self.assertEqual(reason, "Rain > threshold")
    
    def test_check_block_conditions_moisture_block(self):
        """Test that moisture block is detected (BlockReason = 2)"""
        args = MagicMock()
        args.host = "127.0.0.1"
        args.port = 502
        args.unit = 1
        
        # Mock Modbus client to return BlockReason = 2 (moisture)
        with patch('bevattning_scheduler.bevattning_controller.ModbusTcpClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = True
            
            mock_result = MagicMock()
            mock_result.registers = [2]  # BlockReason = 2 (moisture)
            mock_client.read_holding_registers.return_value = mock_result
            
            with patch('bevattning_scheduler.bevattning_controller.open_modbus_client', return_value=mock_client):
                should_block, reason = bevattning_scheduler.check_block_conditions(args)
                
                self.assertTrue(should_block)
                self.assertEqual(reason, "Moisture > threshold")
    
    def test_check_block_conditions_estop_block(self):
        """Test that E-stop block is detected (BlockReason = 4)"""
        args = MagicMock()
        args.host = "127.0.0.1"
        args.port = 502
        args.unit = 1
        
        # Mock Modbus client to return BlockReason = 4 (E-stop)
        with patch('bevattning_scheduler.bevattning_controller.ModbusTcpClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = True
            
            mock_result = MagicMock()
            mock_result.registers = [4]  # BlockReason = 4 (E-stop)
            mock_client.read_holding_registers.return_value = mock_result
            
            with patch('bevattning_scheduler.bevattning_controller.open_modbus_client', return_value=mock_client):
                should_block, reason = bevattning_scheduler.check_block_conditions(args)
                
                self.assertTrue(should_block)
                self.assertEqual(reason, "E-stop active")
    
    def test_run_scheduled_watering_blocked(self):
        """Test that watering is skipped when conditions are blocked"""
        args = MagicMock()
        args.host = "127.0.0.1"
        args.port = 502
        args.unit = 1
        
        # Mock check_block_conditions to return blocked
        with patch('bevattning_scheduler.check_block_conditions', return_value=(True, "Rain > threshold")):
            with patch('bevattning_scheduler.bevattning_controller.main_once') as mock_main_once:
                bevattning_scheduler.run_scheduled_watering(args)
                
                # main_once should NOT be called when blocked
                mock_main_once.assert_not_called()
    
    def test_run_scheduled_watering_not_blocked(self):
        """Test that watering runs when conditions are OK"""
        args = MagicMock()
        args.host = "127.0.0.1"
        args.port = 502
        args.unit = 1
        
        # Mock check_block_conditions to return not blocked
        with patch('bevattning_scheduler.check_block_conditions', return_value=(False, None)):
            with patch('bevattning_scheduler.bevattning_controller.main_once', return_value={"temp": 15, "rain24h": 0}) as mock_main_once:
                bevattning_scheduler.run_scheduled_watering(args)
                
                # main_once SHOULD be called when not blocked
                mock_main_once.assert_called_once_with(args)


class TestScheduleTime(unittest.TestCase):
    """Test cases for schedule time configuration"""
    
    def test_default_schedule_time(self):
        """Test that default schedule is 01:00"""
        self.assertEqual(bevattning_scheduler.DEFAULT_SCHEDULE_HOUR, 1)
        self.assertEqual(bevattning_scheduler.DEFAULT_SCHEDULE_MINUTE, 0)


if __name__ == '__main__':
    unittest.main()
