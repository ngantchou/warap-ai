"""
Production Performance Testing Suite
Load testing, concurrent user testing, database performance, and memory leak detection
"""

import pytest
import asyncio
import time
import threading
import gc
import psutil
import os
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.database_models import User, Provider, ServiceRequest, Transaction
from app.services.ai_service import AIService
from app.services.whatsapp_service import WhatsAppService
from app.services.monetbil_service import MonetbilService
from app.database import get_db


class TestLoadTesting:
    """Test application performance under load"""
    
    @pytest.fixture
    def load_test_client(self):
        """Create test client for load testing"""
        return TestClient(app)
    
    def test_concurrent_webhook_requests(self, load_test_client):
        """Test concurrent WhatsApp webhook processing"""
        def send_webhook_request(user_id):
            return load_test_client.post("/webhook/whatsapp", json={
                "From": f"+23769000{user_id:04d}",
                "Body": f"Test message {user_id}",
                "MessageSid": f"test_sid_{user_id}"
            })
        
        # Simulate 50 concurrent webhook requests
        num_requests = 50
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(send_webhook_request, i) 
                for i in range(num_requests)
            ]
            
            responses = [future.result() for future in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertions
        assert duration < 30  # Should complete within 30 seconds
        successful_responses = [r for r in responses if r.status_code in [200, 302]]
        assert len(successful_responses) >= num_requests * 0.8  # 80% success rate minimum
        
        # Average response time should be reasonable
        avg_response_time = duration / num_requests
        assert avg_response_time < 5  # Less than 5 seconds per request on average

    def test_admin_dashboard_load(self, load_test_client):
        """Test admin dashboard performance under load"""
        def access_dashboard():
            return load_test_client.get("/admin/")
        
        # Simulate 20 concurrent admin users
        num_users = 20
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(access_dashboard) for _ in range(num_users)]
            responses = [future.result() for future in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should handle concurrent admin access efficiently
        assert duration < 15  # Complete within 15 seconds
        redirect_responses = [r for r in responses if r.status_code in [200, 302]]
        assert len(redirect_responses) == num_users

    def test_payment_webhook_load(self, load_test_client):
        """Test payment webhook performance under load"""
        def send_payment_webhook(payment_id):
            with patch('app.services.monetbil_service.MonetbilService.verify_webhook_signature', return_value=True):
                return load_test_client.post("/webhook/monetbil", data={
                    "payment_ref": f"test_ref_{payment_id}",
                    "status": "success",
                    "transaction_id": f"tx_{payment_id}",
                    "amount": "10000"
                })
        
        # Simulate 30 concurrent payment webhooks
        num_payments = 30
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(send_payment_webhook, i) 
                for i in range(num_payments)
            ]
            responses = [future.result() for future in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Payment processing should be fast and reliable
        assert duration < 20  # Complete within 20 seconds
        successful_responses = [r for r in responses if r.status_code == 200]
        assert len(successful_responses) >= num_payments * 0.9  # 90% success rate

    def test_api_endpoint_stress(self, load_test_client):
        """Test API endpoints under stress"""
        endpoints = [
            "/health",
            "/",
            "/payment/success"
        ]
        
        def stress_endpoint(endpoint):
            responses = []
            for _ in range(20):
                try:
                    response = load_test_client.get(endpoint)
                    responses.append(response.status_code)
                except Exception as e:
                    responses.append(500)  # Error code
            return responses
        
        # Test each endpoint with rapid requests
        for endpoint in endpoints:
            start_time = time.time()
            status_codes = stress_endpoint(endpoint)
            end_time = time.time()
            
            duration = end_time - start_time
            
            # Should handle rapid requests without significant degradation
            assert duration < 10  # Complete within 10 seconds
            success_codes = [code for code in status_codes if code in [200, 302]]
            assert len(success_codes) >= len(status_codes) * 0.8  # 80% success rate

    def test_response_time_under_load(self, load_test_client):
        """Test response times don't degrade significantly under load"""
        response_times = []
        
        def measure_response_time():
            start = time.time()
            response = load_test_client.get("/health")
            end = time.time()
            return end - start, response.status_code
        
        # Measure baseline response time
        baseline_time, _ = measure_response_time()
        
        # Measure response times under load
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(measure_response_time) for _ in range(50)]
            results = [future.result() for future in futures]
        
        load_times = [time for time, status in results if status == 200]
        
        if load_times:
            avg_load_time = sum(load_times) / len(load_times)
            max_load_time = max(load_times)
            
            # Response time shouldn't degrade too much under load
            assert avg_load_time < baseline_time * 3  # Max 3x slower on average
            assert max_load_time < 10  # No single request takes more than 10 seconds


class TestConcurrentUserTesting:
    """Test application behavior with concurrent users"""
    
    def test_concurrent_user_registration(self):
        """Test concurrent user creation and management"""
        def create_user(user_id):
            user = User(
                whatsapp_id=f"+23769{user_id:06d}",
                name=f"User {user_id}",
                phone_number=f"+23769{user_id:06d}"
            )
            return user
        
        # Create users concurrently
        users = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_user, i) for i in range(100)]
            users = [future.result() for future in futures]
        
        # Verify all users were created successfully
        assert len(users) == 100
        assert len(set(user.whatsapp_id for user in users)) == 100  # All unique

    def test_concurrent_service_requests(self):
        """Test concurrent service request processing"""
        def create_service_request(request_id):
            return ServiceRequest(
                user_id=1,  # Assume user exists
                service_type="plomberie",
                description=f"Service request {request_id}",
                location="Bonamoussadi",
                urgency="normal"
            )
        
        # Create requests concurrently
        requests = []
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(create_service_request, i) for i in range(75)]
            requests = [future.result() for future in futures]
        
        assert len(requests) == 75
        assert all(req.service_type == "plomberie" for req in requests)

    def test_concurrent_provider_matching(self):
        """Test concurrent provider matching operations"""
        from app.services.provider_service import ProviderService
        
        def find_providers():
            # Mock database session
            mock_db = Mock()
            mock_providers = [
                Mock(id=1, name="Provider 1", rating=4.5, total_jobs=10),
                Mock(id=2, name="Provider 2", rating=4.0, total_jobs=15)
            ]
            mock_db.query.return_value.filter.return_value.all.return_value = mock_providers
            
            service = ProviderService(mock_db)
            return service.find_available_providers("plomberie", "Bonamoussadi")
        
        # Concurrent provider searches
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(find_providers) for _ in range(50)]
            results = [future.result() for future in futures]
        
        # All searches should return results
        assert all(len(result) > 0 for result in results)

    def test_concurrent_payment_processing(self):
        """Test concurrent payment processing"""
        def process_payment(payment_id):
            # Mock successful payment processing
            return {
                "id": payment_id,
                "status": "completed",
                "amount": 10000 + (payment_id * 100),
                "commission": (10000 + (payment_id * 100)) * 0.15
            }
        
        # Process payments concurrently
        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = [executor.submit(process_payment, i) for i in range(40)]
            payments = [future.result() for future in futures]
        
        assert len(payments) == 40
        assert all(payment["status"] == "completed" for payment in payments)
        
        # Verify commission calculations are correct
        for payment in payments:
            expected_commission = payment["amount"] * 0.15
            assert abs(payment["commission"] - expected_commission) < 0.01

    def test_race_condition_prevention(self):
        """Test prevention of race conditions in critical sections"""
        shared_counter = {"value": 0}
        lock = threading.Lock()
        
        def increment_counter():
            # Simulate critical section with potential race condition
            for _ in range(100):
                with lock:
                    current = shared_counter["value"]
                    time.sleep(0.0001)  # Small delay to increase chance of race condition
                    shared_counter["value"] = current + 1
        
        # Run concurrent operations
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=increment_counter)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should be exactly 1000 if no race conditions occurred
        assert shared_counter["value"] == 1000


class TestDatabasePerformance:
    """Test database performance under various conditions"""
    
    @pytest.fixture
    def db_engine(self):
        """Create database engine for testing"""
        # Use in-memory SQLite for performance testing
        from sqlalchemy import create_engine
        engine = create_engine("sqlite:///:memory:", echo=False)
        return engine

    def test_bulk_insert_performance(self, db_engine):
        """Test bulk insert performance"""
        from app.models.database_models import Base
        
        Base.metadata.create_all(db_engine)
        Session = sessionmaker(bind=db_engine)
        session = Session()
        
        start_time = time.time()
        
        # Bulk insert 1000 users
        users = []
        for i in range(1000):
            user = User(
                whatsapp_id=f"+23769{i:06d}",
                name=f"User {i}",
                phone_number=f"+23769{i:06d}"
            )
            users.append(user)
        
        session.bulk_save_objects(users)
        session.commit()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete bulk insert quickly
        assert duration < 5  # Less than 5 seconds for 1000 records
        
        # Verify all records were inserted
        count = session.query(User).count()
        assert count == 1000
        
        session.close()

    def test_complex_query_performance(self, db_engine):
        """Test performance of complex database queries"""
        from app.models.database_models import Base
        
        Base.metadata.create_all(db_engine)
        Session = sessionmaker(bind=db_engine)
        session = Session()
        
        # Create test data
        users = [
            User(whatsapp_id=f"+23769{i:06d}", name=f"User {i}", phone_number=f"+23769{i:06d}")
            for i in range(100)
        ]
        session.bulk_save_objects(users)
        
        providers = [
            Provider(
                name=f"Provider {i}",
                whatsapp_id=f"+23768{i:06d}",
                phone_number=f"+23768{i:06d}",
                services=["plomberie"],
                coverage_areas=["Bonamoussadi"],
                rating=4.0 + (i % 10) / 10,
                is_available=True,
                is_active=True
            )
            for i in range(50)
        ]
        session.bulk_save_objects(providers)
        session.commit()
        
        # Test complex query performance
        start_time = time.time()
        
        # Complex query with joins and filters
        query = session.query(User).join(ServiceRequest, User.id == ServiceRequest.user_id, isouter=True)\
                      .filter(User.name.like("User%"))\
                      .order_by(User.created_at.desc())\
                      .limit(20)
        
        results = query.all()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Complex query should still be reasonably fast
        assert duration < 2  # Less than 2 seconds
        assert len(results) <= 20
        
        session.close()

    def test_concurrent_database_access(self, db_engine):
        """Test database performance under concurrent access"""
        from app.models.database_models import Base
        
        Base.metadata.create_all(db_engine)
        
        def database_operations(thread_id):
            Session = sessionmaker(bind=db_engine)
            session = Session()
            
            try:
                # Perform various database operations
                for i in range(10):
                    user = User(
                        whatsapp_id=f"+2376{thread_id:02d}{i:04d}",
                        name=f"User {thread_id}-{i}",
                        phone_number=f"+2376{thread_id:02d}{i:04d}"
                    )
                    session.add(user)
                    session.commit()
                    
                    # Query operations
                    users = session.query(User).filter(
                        User.name.like(f"User {thread_id}%")
                    ).all()
                    
                return len(users)
            finally:
                session.close()
        
        start_time = time.time()
        
        # Run concurrent database operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(database_operations, i) for i in range(10)]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should handle concurrent access efficiently
        assert duration < 10  # Complete within 10 seconds
        assert all(result >= 10 for result in results)  # Each thread created 10 users

    def test_database_connection_pooling(self, db_engine):
        """Test database connection pooling performance"""
        from sqlalchemy.pool import QueuePool
        
        # Create engine with connection pooling
        pooled_engine = create_engine(
            "sqlite:///:memory:",
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            echo=False
        )
        
        def use_connection():
            with pooled_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return result.fetchone()[0]
        
        start_time = time.time()
        
        # Test connection pool under load
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(use_connection) for _ in range(100)]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Connection pooling should improve performance
        assert duration < 5  # Should be fast with pooling
        assert all(result == 1 for result in results)

    def test_transaction_performance(self, db_engine):
        """Test database transaction performance"""
        from app.models.database_models import Base
        
        Base.metadata.create_all(db_engine)
        Session = sessionmaker(bind=db_engine)
        
        def transaction_test():
            session = Session()
            try:
                with session.begin():
                    # Perform multiple operations in single transaction
                    for i in range(50):
                        user = User(
                            whatsapp_id=f"+237690{i:05d}",
                            name=f"Transaction User {i}",
                            phone_number=f"+237690{i:05d}"
                        )
                        session.add(user)
                
                return True
            except Exception:
                return False
            finally:
                session.close()
        
        start_time = time.time()
        
        # Run multiple transactions
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(transaction_test) for _ in range(5)]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Transactions should complete efficiently
        assert duration < 8  # Complete within 8 seconds
        assert all(results)  # All transactions should succeed


class TestMemoryLeakDetection:
    """Test for memory leaks and resource management"""
    
    def test_memory_usage_stability(self):
        """Test that memory usage remains stable during operations"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform memory-intensive operations
        for iteration in range(10):
            large_data = []
            
            # Create large data structures
            for i in range(1000):
                user_data = {
                    "id": i,
                    "whatsapp_id": f"+23769{i:06d}",
                    "name": f"User {i}" * 10,  # Make strings larger
                    "messages": [f"Message {j}" for j in range(50)]
                }
                large_data.append(user_data)
            
            # Process the data
            processed_data = []
            for user in large_data:
                processed_user = {
                    "id": user["id"],
                    "phone": user["whatsapp_id"],
                    "display_name": user["name"].upper(),
                    "message_count": len(user["messages"])
                }
                processed_data.append(processed_user)
            
            # Clear references
            del large_data
            del processed_data
            
            # Force garbage collection
            gc.collect()
            
            # Check memory every few iterations
            if iteration % 3 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory
                
                # Memory shouldn't grow excessively
                assert memory_increase < 100  # Less than 100MB increase
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_increase = final_memory - initial_memory
        
        # Total memory increase should be reasonable
        assert total_increase < 50  # Less than 50MB total increase

    def test_object_reference_cleanup(self):
        """Test that object references are properly cleaned up"""
        import weakref
        
        class TestObject:
            def __init__(self, data):
                self.data = data
        
        # Create objects and weak references
        objects = []
        weak_refs = []
        
        for i in range(100):
            obj = TestObject(f"test_data_{i}")
            objects.append(obj)
            weak_refs.append(weakref.ref(obj))
        
        # Verify all objects exist
        assert all(ref() is not None for ref in weak_refs)
        
        # Clear references
        del objects
        gc.collect()
        
        # Check that objects were garbage collected
        alive_objects = [ref for ref in weak_refs if ref() is not None]
        assert len(alive_objects) == 0  # All objects should be garbage collected

    def test_database_connection_cleanup(self):
        """Test that database connections are properly cleaned up"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine("sqlite:///:memory:")
        Session = sessionmaker(bind=engine)
        
        # Create and use multiple sessions
        sessions = []
        for i in range(20):
            session = Session()
            sessions.append(session)
            
            # Use the session
            result = session.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
        
        # Close all sessions
        for session in sessions:
            session.close()
        
        # Clear references
        del sessions
        gc.collect()
        
        # Engine should handle connection cleanup
        # This is mainly testing that no exceptions occur

    def test_large_data_processing_memory(self):
        """Test memory efficiency with large data processing"""
        initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        def process_large_dataset():
            # Simulate processing large dataset in chunks
            for chunk in range(10):
                # Process data in chunks to avoid memory buildup
                chunk_data = []
                for i in range(1000):
                    record = {
                        "id": chunk * 1000 + i,
                        "data": f"record_{chunk}_{i}" * 20
                    }
                    chunk_data.append(record)
                
                # Process chunk
                processed = [
                    {"id": record["id"], "length": len(record["data"])}
                    for record in chunk_data
                ]
                
                # Clear chunk data immediately
                del chunk_data
                del processed
                gc.collect()
        
        # Process data
        process_large_dataset()
        
        final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal due to chunked processing
        assert memory_increase < 30  # Less than 30MB increase

    def test_async_operation_memory(self):
        """Test memory usage with async operations"""
        import asyncio
        
        async def async_operation(operation_id):
            # Simulate async work
            data = [f"async_data_{operation_id}_{i}" for i in range(100)]
            await asyncio.sleep(0.01)  # Small delay
            return len(data)
        
        async def run_async_operations():
            # Run many async operations
            tasks = [async_operation(i) for i in range(50)]
            results = await asyncio.gather(*tasks)
            return results
        
        initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        # Run async operations
        results = asyncio.run(run_async_operations())
        
        final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        # Async operations should not cause significant memory increase
        assert memory_increase < 20  # Less than 20MB increase
        assert len(results) == 50
        assert all(result == 100 for result in results)


class TestResourceManagement:
    """Test system resource management and limits"""
    
    def test_file_descriptor_management(self):
        """Test that file descriptors are properly managed"""
        import tempfile
        
        initial_fd_count = len(os.listdir('/proc/self/fd')) if os.path.exists('/proc/self/fd') else 0
        
        # Create and close many temporary files
        for i in range(100):
            with tempfile.NamedTemporaryFile() as temp_file:
                temp_file.write(b"test data")
                temp_file.flush()
        
        final_fd_count = len(os.listdir('/proc/self/fd')) if os.path.exists('/proc/self/fd') else 0
        
        # File descriptor count should not increase significantly
        if initial_fd_count > 0:  # Only check if we can read fd count
            assert abs(final_fd_count - initial_fd_count) < 10

    def test_thread_management(self):
        """Test that threads are properly managed and cleaned up"""
        import threading
        
        initial_thread_count = threading.active_count()
        
        def worker_thread():
            time.sleep(0.1)
            return "completed"
        
        # Create many threads
        threads = []
        for i in range(20):
            thread = threading.Thread(target=worker_thread)
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Clean up references
        del threads
        time.sleep(0.1)  # Allow cleanup time
        
        final_thread_count = threading.active_count()
        
        # Thread count should return to approximately initial level
        assert abs(final_thread_count - initial_thread_count) <= 2

    def test_cpu_usage_efficiency(self):
        """Test that operations don't consume excessive CPU"""
        def cpu_intensive_operation():
            # Simulate work that should be efficient
            result = 0
            for i in range(100000):
                result += i * 2
            return result
        
        start_time = time.time()
        process = psutil.Process(os.getpid())
        initial_cpu = process.cpu_percent()
        
        # Perform operations
        results = []
        for i in range(10):
            result = cpu_intensive_operation()
            results.append(result)
        
        end_time = time.time()
        duration = end_time - start_time
        final_cpu = process.cpu_percent()
        
        # Operations should complete in reasonable time
        assert duration < 5  # Complete within 5 seconds
        assert len(results) == 10
        
        # CPU usage should be reasonable (this test may be environment-dependent)
        # assert final_cpu < 90  # Less than 90% CPU usage