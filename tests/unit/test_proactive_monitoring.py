"""
Test script for proactive monitoring system
"""
import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import get_db
from app.services.proactive_monitoring_service import ProactiveMonitoringService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

async def test_proactive_monitoring():
    """Test proactive monitoring system"""
    print("🔍 PROACTIVE MONITORING SYSTEM TEST")
    print("=" * 50)
    
    try:
        # Initialize database and monitoring service
        db = next(get_db())
        try:
            monitoring_service = ProactiveMonitoringService(db)
            
            # Test system health status
            print("\n🏥 SYSTEM HEALTH STATUS")
            print("-" * 30)
            health_status = await monitoring_service.get_system_health_status()
            
            print(f"Health Status: {health_status['health_status'].upper()}")
            print(f"Success Rate: {health_status['success_rate']}%")
            print(f"Active Requests: {health_status['active_requests']}")
            print(f"Failed Notifications (1h): {health_status['failed_notifications_1h']}")
            print(f"Successful Notifications (1h): {health_status['successful_notifications_1h']}")
            print(f"Pending Retries: {health_status['pending_retries']}")
            print(f"Long Running Requests: {health_status['long_running_requests']}")
            
            print("\n📋 RECOMMENDATIONS:")
            for i, rec in enumerate(health_status.get('recommendations', []), 1):
                print(f"  {i}. {rec}")
            
            # Test detailed error analysis
            print("\n🔍 DETAILED ERROR ANALYSIS")
            print("-" * 30)
            error_analysis = await monitoring_service.get_detailed_error_analysis()
            
            print(f"Recent Errors: {len(error_analysis.get('recent_errors', []))}")
            
            error_patterns = error_analysis.get('error_patterns', {})
            if error_patterns:
                print("Error Patterns:")
                for error_type, count in error_patterns.items():
                    print(f"  - {error_type}: {count} occurrences")
            
            problematic_requests = error_analysis.get('problematic_requests', [])
            if problematic_requests:
                print(f"Problematic Requests: {len(problematic_requests)}")
                for req in problematic_requests[:3]:  # Show first 3
                    print(f"  - Request {req['id']}: {req['service_type']} ({req['minutes_elapsed']} min)")
            
            # Test proactive update status
            print("\n🔄 PROACTIVE UPDATE STATUS")
            print("-" * 30)
            proactive_status = await monitoring_service.get_proactive_update_status()
            
            print(f"Total Active Requests: {proactive_status['total_active_requests']}")
            print(f"Requests Needing Attention: {proactive_status['requests_needing_attention']}")
            
            performance = proactive_status.get('system_performance', {})
            print(f"Average Processing Time: {performance.get('average_processing_time', 0)} minutes")
            print(f"Success Rate (24h): {performance.get('success_rate_24h', 0)}%")
            print(f"Provider Response Rate: {performance.get('provider_response_rate', 0)}%")
            
            # Test comprehensive monitoring report
            print("\n📊 COMPREHENSIVE MONITORING REPORT")
            print("-" * 40)
            report = await monitoring_service.generate_monitoring_report()
            
            summary = report.get('summary', {})
            print(f"Overall Status: {summary.get('overall_status', 'unknown').upper()}")
            print(f"Immediate Actions Needed: {'YES' if summary.get('immediate_actions_needed') else 'NO'}")
            
            primary_issues = summary.get('primary_issues', [])
            if primary_issues:
                print("Primary Issues:")
                for issue in primary_issues:
                    print(f"  - {issue}")
            
            # Generate status indicator
            overall_status = summary.get('overall_status', 'unknown')
            if overall_status == 'healthy':
                status_indicator = "🟢 HEALTHY"
            elif overall_status == 'degraded':
                status_indicator = "🟡 DEGRADED"
            elif overall_status == 'critical':
                status_indicator = "🔴 CRITICAL"
            else:
                status_indicator = "⚪ UNKNOWN"
            
            print(f"\n{status_indicator}")
            print(f"Report generated at: {report['report_timestamp']}")
            
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in proactive monitoring test: {e}")
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Run the proactive monitoring test"""
    try:
        result = asyncio.run(test_proactive_monitoring())
        if result:
            print("\n✅ Proactive monitoring test completed successfully")
        else:
            print("\n❌ Proactive monitoring test failed")
    except Exception as e:
        print(f"❌ Error running test: {e}")

if __name__ == "__main__":
    main()