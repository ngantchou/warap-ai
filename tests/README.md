# Djobea AI Test Suite

Professional test organization for comprehensive system testing.

## Test Structure

```
tests/
├── api/           # API endpoint tests
├── integration/   # Integration tests
├── services/      # Service layer tests
├── unit/          # Unit tests
├── models/        # Database model tests
├── fixtures/      # Test fixtures and utilities
├── conftest.py    # Global test configuration
├── pytest.ini    # Pytest configuration
└── README.md      # This file
```

## Test Categories

### API Tests (`tests/api/`)
- `test_api_endpoints.py` - Core API endpoint validation
- `test_clean_api.py` - Clean API structure tests
- `test_comprehensive_api_complete.py` - Complete API suite tests
- `test_dashboard_endpoints.py` - Dashboard API tests
- `test_admin_auth_api.py` - Admin authentication API tests

### Integration Tests (`tests/integration/`)
- `test_complete_system_integration.py` - Full system integration
- `test_complete_admin_auth_integration.py` - Admin auth integration
- `test_complete_notification_flow.py` - Notification system integration
- `test_complete_web_chat_notification_system.py` - Web chat integration
- `test_conversational_request_integration.py` - Conversation integration

### Service Tests (`tests/services/`)
- `test_ai_suggestions_system.py` - AI suggestions service
- `test_multi_llm_system.py` - Multi-LLM service
- `test_multi_llm_conversational_system.py` - Conversational AI
- `test_error_handling_system.py` - Error handling service
- `test_enhanced_communication.py` - Communication service
- `test_enhanced_features.py` - Enhanced features

### Unit Tests (`tests/unit/`)
- Dialog flow tests
- System component tests
- Individual feature tests
- Utility function tests

### Model Tests (`tests/models/`)
- `test_action_code_system.py` - Action code models
- `test_integration_conversationnelle_base_connaissance.py` - Knowledge base models
- `test_agent_dashboard_communication.py` - Agent dashboard models

## Running Tests

### Basic Commands
```bash
# Run all tests
pytest tests/

# Run specific test category
pytest tests/api/
pytest tests/integration/
pytest tests/services/
pytest tests/unit/
pytest tests/models/

# Run with coverage
pytest --cov=app tests/

# Run with verbose output
pytest -v tests/

# Run specific test file
pytest tests/api/test_api_endpoints.py

# Run specific test function
pytest tests/api/test_api_endpoints.py::test_analytics_endpoint
```

### Test Markers
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only API tests
pytest -m api

# Run only service tests
pytest -m services

# Skip slow tests
pytest -m "not slow"

# Run only authentication tests
pytest -m auth

# Run only database tests
pytest -m database
```

### Advanced Testing
```bash
# Run tests in parallel
pytest -n auto tests/

# Run tests with HTML report
pytest --html=reports/report.html tests/

# Run tests with JUnit XML output
pytest --junitxml=reports/junit.xml tests/

# Run tests with coverage report
pytest --cov=app --cov-report=html tests/
```

## Test Configuration

### Environment Variables
Tests use the following environment variables:
- `TESTING=true` - Enables test mode
- `DATABASE_URL=sqlite:///test_djobea.db` - Test database
- `OPENAI_API_KEY` - For AI service tests
- `TWILIO_ACCOUNT_SID` - For messaging tests
- `TWILIO_AUTH_TOKEN` - For messaging tests

### Test Database
Tests use an isolated SQLite database to avoid affecting production data.

### Fixtures
Common test fixtures are available in `tests/fixtures/common.py`:
- `sample_conversation_context` - Sample conversation data
- `auth_headers` - Authentication headers
- `TestUtils` - Utility functions for testing

## Writing Tests

### Test File Naming
- API tests: `test_api_*.py`
- Integration tests: `test_*_integration.py`
- Service tests: `test_*_service.py`
- Unit tests: `test_*.py`

### Test Function Naming
- Use descriptive names: `test_user_registration_with_valid_data`
- Use consistent patterns: `test_<feature>_<scenario>_<expected_result>`

### Test Structure
```python
def test_feature_scenario_expected_result():
    # Arrange
    test_data = create_test_data()
    
    # Act
    result = function_under_test(test_data)
    
    # Assert
    assert result.status == "success"
    assert result.data is not None
```

## Continuous Integration

Tests are configured to run automatically on:
- Pull requests
- Main branch pushes
- Scheduled runs

## Test Reports

Test results and coverage reports are generated in the `reports/` directory:
- `reports/coverage/` - Coverage reports
- `reports/junit.xml` - JUnit XML results
- `reports/report.html` - HTML test report

## Best Practices

1. **Isolation**: Each test should be independent
2. **Descriptive**: Test names should clearly describe what is being tested
3. **Fast**: Unit tests should run quickly
4. **Reliable**: Tests should not be flaky
5. **Maintainable**: Tests should be easy to update when code changes
6. **Comprehensive**: Cover happy path, edge cases, and error conditions

## Contributing

When adding new tests:
1. Place them in the appropriate category directory
2. Follow the naming conventions
3. Use existing fixtures when possible
4. Add appropriate test markers
5. Update this README if needed

## Support

For questions about testing:
- Check existing test files for examples
- Review the fixtures in `tests/fixtures/`
- Check the configuration in `conftest.py`
- Refer to pytest documentation