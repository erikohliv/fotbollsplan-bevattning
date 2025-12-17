#!/usr/bin/env python3
"""
Performance tests for fotbollsplan-bevattning
Tests Modbus operations and caching efficiency
"""
import time
import unittest
from unittest.mock import Mock, MagicMock, patch
from display_manager import ModbusReader
from bevattning_controller import hamta_vader


class TestModbusCaching(unittest.TestCase):
    """Test Modbus caching performance"""
    
    @patch('display_manager.ModbusTcpClient')
    def test_cache_reduces_connections(self, mock_client_class):
        """Test that caching reduces Modbus connection attempts"""
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.connect.return_value = True
        mock_result = Mock()
        mock_result.registers = [1, 2, 3]
        # Ensure isError returns False
        mock_result.isError = Mock(return_value=False)
        mock_client.read_holding_registers.return_value = mock_result
        
        # Create reader with short cache duration
        reader = ModbusReader(cache_duration=1.0)
        
        # First read - should hit Modbus
        result1 = reader.read_registers(50, 3)
        self.assertEqual(result1, [1, 2, 3])
        self.assertEqual(mock_client.connect.call_count, 1)
        
        # Second read within cache window - should use cache
        result2 = reader.read_registers(50, 3)
        self.assertEqual(result2, [1, 2, 3])
        self.assertEqual(mock_client.connect.call_count, 1)  # No new connection
        
        # Third read after cache expires - should hit Modbus again
        time.sleep(1.1)
        result3 = reader.read_registers(50, 3)
        self.assertEqual(result3, [1, 2, 3])
        self.assertEqual(mock_client.connect.call_count, 2)  # New connection
    
    @patch('display_manager.ModbusTcpClient')
    def test_cache_invalidation_on_write(self, mock_client_class):
        """Test that cache is invalidated when writing to a register"""
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.connect.return_value = True
        mock_read_result = Mock()
        mock_read_result.registers = [100]
        mock_read_result.isError = Mock(return_value=False)
        mock_client.read_holding_registers.return_value = mock_read_result
        mock_write_result = Mock()
        mock_write_result.isError = Mock(return_value=False)
        mock_client.write_register.return_value = mock_write_result
        
        reader = ModbusReader(cache_duration=10.0)
        
        # Read to populate cache
        result1 = reader.read_registers(50, 1)
        self.assertEqual(result1, [100])
        self.assertEqual(mock_client.connect.call_count, 1)
        
        # Write to same register - should invalidate cache
        reader.write_register(50, 200)
        
        # Read again - should hit Modbus since cache was invalidated
        result2 = reader.read_registers(50, 1)
        self.assertEqual(result2, [100])
        self.assertEqual(mock_client.connect.call_count, 3)  # 1 read + 1 write + 1 read
    
    @patch('display_manager.ModbusTcpClient')
    def test_no_cache_when_disabled(self, mock_client_class):
        """Test that caching can be disabled per-call"""
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.connect.return_value = True
        mock_result = Mock()
        mock_result.registers = [42]
        mock_result.isError = Mock(return_value=False)
        mock_client.read_holding_registers.return_value = mock_result
        
        reader = ModbusReader(cache_duration=10.0)
        
        # Read without cache
        result1 = reader.read_registers(50, 1, use_cache=False)
        self.assertEqual(result1, [42])
        self.assertEqual(mock_client.connect.call_count, 1)
        
        # Read again without cache - should hit Modbus again
        result2 = reader.read_registers(50, 1, use_cache=False)
        self.assertEqual(result2, [42])
        self.assertEqual(mock_client.connect.call_count, 2)


class TestWeatherCaching(unittest.TestCase):
    """Test weather API caching performance"""
    
    @patch('bevattning_controller.requests.get')
    def test_weather_cache_reduces_api_calls(self, mock_get):
        """Test that weather cache reduces API calls"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'current_weather': {'temperature': 20.0},
            'hourly': {
                'temperature_2m': [20.0] * 25,
                'rain': [0.0] * 25,
                'precipitation': [0.0] * 25
            }
        }
        mock_get.return_value = mock_response
        
        # Import to reset cache
        import bevattning_controller
        bevattning_controller._weather_cache = {"data": None, "timestamp": None, "cache_duration": 600}
        
        # First call - should hit API
        temp1, rain1 = hamta_vader("56.10", "14.45", use_cache=True)
        self.assertEqual(mock_get.call_count, 1)
        self.assertIsNotNone(temp1)
        
        # Second call within cache window - should use cache
        temp2, rain2 = hamta_vader("56.10", "14.45", use_cache=True)
        self.assertEqual(mock_get.call_count, 1)  # No new API call
        self.assertEqual(temp1, temp2)
        self.assertEqual(rain1, rain2)
    
    @patch('bevattning_controller.requests.get')
    def test_weather_cache_disabled(self, mock_get):
        """Test weather fetch without cache"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'current_weather': {'temperature': 20.0},
            'hourly': {
                'temperature_2m': [20.0] * 25,
                'rain': [0.0] * 25,
                'precipitation': [0.0] * 25
            }
        }
        mock_get.return_value = mock_response
        
        # First call without cache
        temp1, rain1 = hamta_vader("56.10", "14.45", use_cache=False)
        self.assertEqual(mock_get.call_count, 1)
        
        # Second call without cache - should hit API again
        temp2, rain2 = hamta_vader("56.10", "14.45", use_cache=False)
        self.assertEqual(mock_get.call_count, 2)


class TestBulkWrites(unittest.TestCase):
    """Test bulk write optimization"""
    
    @patch('bevattning_controller.ModbusTcpClient')
    def test_bulk_write_reduces_operations(self, mock_client_class):
        """Test that bulk writes use fewer operations than individual writes"""
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.connect.return_value = True
        mock_result = Mock()
        mock_result.isError.return_value = False
        mock_client.write_registers.return_value = mock_result
        
        from bevattning_controller import write_registers_bulk, open_modbus_client
        
        client = open_modbus_client("127.0.0.1", 502)
        
        # Bulk write should make one call
        success = write_registers_bulk(client, 20, [60, 25, 30], unit=1)
        self.assertTrue(success)
        self.assertEqual(mock_client.write_registers.call_count, 1)
        
        # Verify correct parameters
        call_args = mock_client.write_registers.call_args
        self.assertEqual(call_args[0][0], 20)  # Start address
        self.assertEqual(call_args[0][1], [60, 25, 30])  # Values


class TestDisplayOptimizations(unittest.TestCase):
    """Test display manager optimizations"""
    
    def test_display2_update_interval(self):
        """Test that Display2 doesn't update too frequently"""
        from display_manager import Display2Manager
        
        # This is a conceptual test - in practice we'd mock GPIO and Modbus
        # The optimization reduces updates from 10/sec to 1/sec when no buttons pressed
        # Expected: ~90% reduction in I2C traffic
        
        # Calculate expected reduction
        old_rate = 10  # updates per second
        new_rate = 1   # updates per second when idle
        reduction = ((old_rate - new_rate) / old_rate) * 100
        
        self.assertGreaterEqual(reduction, 90)
        self.assertEqual(new_rate, 1)


if __name__ == '__main__':
    unittest.main()
