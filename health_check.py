"""Health check and monitoring utilities for the trading bot."""
import asyncio
import time
from typing import Dict, Any
from datetime import datetime

from config.settings import settings
from utils.logger import logger


class HealthMonitor:
    """Monitors the health of various components in the trading bot."""
    
    def __init__(self):
        """Initialize the health monitor."""
        self._component_status = {}
        self._last_checks = {}
        self._errors = []
        
    def register_component(self, name: str, initial_status: bool = True):
        """Register a new component for monitoring."""
        self._component_status[name] = {
            'status': initial_status,
            'last_update': time.time(),
            'checks_run': 0,
            'errors': 0
        }
        self._last_checks[name] = time.time()
    
    def update_component_status(self, name: str, status: bool, message: str = ""):
        """Update the status of a component."""
        if name in self._component_status:
            self._component_status[name]['status'] = status
            self._component_status[name]['last_update'] = time.time()
            self._component_status[name]['checks_run'] += 1
            
            if not status:
                self._component_status[name]['errors'] += 1
                self._errors.append({
                    'component': name,
                    'timestamp': time.time(),
                    'message': message
                })
                
                # Log error
                logger.warning(f"Component {name} health check failed: {message}")
        else:
            logger.warning(f"Component {name} not registered for health monitoring")
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get a comprehensive health report."""
        report = {
            'timestamp': time.time(),
            'overall_status': all(comp['status'] for comp in self._component_status.values()),
            'components': self._component_status.copy(),
            'total_errors': len(self._errors),
            'recent_errors': self._errors[-10:] if self._errors else []  # Last 10 errors
        }
        return report
    
    def is_healthy(self) -> bool:
        """Check if the overall system is healthy."""
        return all(comp['status'] for comp in self._component_status.values())
    
    async def periodic_check(self, interval: int = 30):
        """Run periodic health checks."""
        while True:
            try:
                # Perform general health checks
                await self._perform_general_checks()
                
                # Log health status periodically
                report = self.get_health_report()
                if not report['overall_status']:
                    logger.warning(f"System health issue detected: {len(report['recent_errors'])} recent errors")
                else:
                    logger.info("System health check passed")
                    
            except Exception as e:
                logger.error(f"Error during health check: {e}")
            
            await asyncio.sleep(interval)
    
    async def _perform_general_checks(self):
        """Perform general system health checks."""
        # Check settings are valid
        try:
            settings.validate()
            self.update_component_status('settings', True)
        except Exception as e:
            self.update_component_status('settings', False, f"Settings validation failed: {e}")
        
        # Add more checks as needed
        pass


# Global health monitor instance
health_monitor = HealthMonitor()


def init_health_monitor():
    """Initialize the health monitor with default components."""
    health_monitor.register_component('telegram_bot', False)  # Will be updated when bot starts
    health_monitor.register_component('websocket_connection', False)  # Will be updated when WS connects
    health_monitor.register_component('database', False)  # Will be updated when DB connects
    health_monitor.register_component('scanner', False)  # Will be updated when scanner starts
    health_monitor.register_component('settings', True)  # Assume initially OK, verify in checks


async def start_health_monitoring():
    """Start the health monitoring service."""
    init_health_monitor()
    await health_monitor.periodic_check()


def get_system_health():
    """Get the current system health status."""
    return health_monitor.get_health_report()


if __name__ == "__main__":
    # Test the health monitor
    async def test_health_monitor():
        init_health_monitor()
        
        # Simulate some status updates
        health_monitor.update_component_status('database', True, 'Database connected successfully')
        health_monitor.update_component_status('telegram_bot', True, 'Bot authenticated successfully')
        health_monitor.update_component_status('websocket_connection', False, 'Connection lost')
        
        report = get_system_health()
        print("Health Report:")
        print(f"Overall Status: {'Healthy' if report['overall_status'] else 'Unhealthy'}")
        print(f"Total Errors: {report['total_errors']}")
        print("Component Status:")
        for comp, status in report['components'].items():
            print(f"  {comp}: {'OK' if status['status'] else 'ERROR'} ({status['checks_run']} checks, {status['errors']} errors)")
    
    asyncio.run(test_health_monitor())