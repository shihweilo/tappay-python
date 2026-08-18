# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2025-12-17

### Added
- **Pydantic v2 Integration**: Migrated `CardHolderData` model to use Pydantic v2's `BaseModel`
  - Automatic data validation with clear error messages
  - Email validation using `EmailStr` type
  - Type safety and IDE autocomplete support
  - Automatic serialization/deserialization
  - JSON schema generation for API documentation
- Added `email-validator` dependency for email validation
- Added example file demonstrating Pydantic v2 validation features (`examples/pydantic_validation.py`)

### Changed
- `CardHolderData` now requires keyword arguments instead of positional arguments (Pydantic v2 requirement)
- Updated `to_dict()` method to use Pydantic's `model_dump()` for better performance
- Bumped version to 0.6.0

### Migration Guide
If you were using positional arguments:
```python
# Old (v0.5.x)
card_holder = Models.CardHolderData("0912345678", "Wang Xiao Ming", "test@example.com")

# New (v0.6.0+)
card_holder = Models.CardHolderData(
    phone_number="0912345678",
    name="Wang Xiao Ming",
    email="test@example.com"
)
```

## [0.5.2] - 2024-XX-XX

### Changed
- Previous version before Pydantic integration
