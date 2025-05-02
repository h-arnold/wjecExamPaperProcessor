# MongoDB Integration Action Plan

## Overview

This document outlines the step-by-step action plan for integrating MongoDB into the WJEC Exam Paper Processor, consolidating the two-stage process (metadata extraction and hierarchical indexing) into a single database-driven workflow.

## Current Architecture

1. `MetadataExtractor` extracts metadata and builds flat index (`Index/index.json`)
2. `IndexManager` transforms this into hierarchical index (`Index/hierarchical_index.json`)

## Integration Goals

- Eliminate the intermediary JSON files as the primary data store
- Maintain JSON files as backups and for compatibility
- Leverage MongoDB's query capabilities for improved performance
- Ensure real-time data updates with consistent relationships

## Implementation Steps

### Step 1: Set Up MongoDB Connection Management

**Estimated time**: 1-2 days

#### Methods to Create

- `DBManager.connect()` - Establish connection to MongoDB
- `DBManager.disconnect()` - Close MongoDB connection
- `DBManager.get_database()` - Return database instance

#### Methods to Modify

- None (new functionality)

#### Testing Criteria

- Connection can be established to MongoDB
- Connection string is properly read from environment variables
- Appropriate error handling for connection failures

#### Progress Log

- [x] Created connection management methods
- [x] Implemented environment variable configuration
- [x] Added error handling
- [x] Tested connection functionality

**Implementation Notes (2 May 2025):**

- Discovered that the existing `DBManager` class already had most of the required functionality
- Added `disconnect()` method as an alias for the existing `close_connection()` method to ensure naming consistency
- Added unit test for the new `disconnect()` method
- All tests now pass successfully
- Connection management fully supports environment variable configuration with appropriate defaults
- Comprehensive error handling for connection failures implemented

---

### Step 2: Create Basic Document Storage Functionality

**Estimated time**: 2-3 days

#### Methods to Create

- `DBManager.save_exam_metadata(metadata, document_id)` - Store extracted metadata in MongoDB
- `DBManager.get_exam_metadata(document_id)` - Retrieve a specific document
- `DBManager.delete_exam_metadata(document_id)` - Remove a document

#### Methods to Reuse

- `MetadataExtractor.extract_metadata()` - No changes needed
- `DocumentProcessor.process_document()` - Will be modified later

#### Testing Criteria

- Documents can be stored in MongoDB
- Documents can be retrieved by ID
- Documents can be deleted
- Proper handling of duplicate documents
- Validation of required fields

#### Progress Log

- [x] Implemented save functionality
- [x] Implemented retrieval functionality
- [x] Implemented deletion functionality
- [x] Added validation logic
- [x] Created tests for CRUD operations

**Implementation Notes (2 May 2025):**

- Implemented three core methods for handling exam metadata:
  - `save_exam_metadata(metadata, document_id)` - For storing metadata in MongoDB
  - `get_exam_metadata(document_id)` - For retrieving documents by ID
  - `delete_exam_metadata(document_id)` - For removing documents
- Added a utility method `document_exists(document_id)` to check if a document already exists in the database
- Implemented validation for required fields in metadata ('subject', 'qualification', 'year', 'season', 'unit')
- Added automatic generation of document IDs when not explicitly provided
- Created comprehensive test suite with 10 test cases covering all methods
- All methods include proper error handling and logging
- Updated datetime handling to use timezone-aware objects (datetime.datetime.now(UTC)) as per best practices
- Fixed a bug with pymongo datetime handling
- All 24 tests now pass successfully without warnings

---

### Step 3: Modify Document Processing Flow

**Estimated time**: 3-4 days

#### Methods to Modify

- `DocumentProcessor.process_document()` - Update to write to MongoDB
- `MetadataFileManager.write_metadata_to_file()` - Make optional for backup purposes

#### Methods to Create

- `DBManager.document_exists(document_id)` - Check if document already exists in MongoDB

#### Testing Criteria

- Processing a document writes to both MongoDB and JSON backup
- Duplicate detection works correctly
- Error handling preserves data integrity
- Performance is not significantly impacted

#### Progress Log

- [ ] Modified document processing flow
- [ ] Implemented MongoDB write operations
- [ ] Added backup file writing logic
- [ ] Tested with sample documents
- [ ] Validated error handling

---

### Step 4: Implement Relationship Management

**Estimated time**: 2-3 days

#### Methods to Create

- `DBManager.update_document_relationships(document_id)` - Set relationships for a document
- `DBManager.find_related_documents(document_id)` - Find related mark schemes/question papers

#### Methods to Reuse

- `IndexManager._update_related_documents()` - Adapt logic for MongoDB

#### Testing Criteria

- Related documents are correctly identified
- Relationships are bidirectional
- Updates to one document correctly update relationships

#### Progress Log

- [ ] Implemented relationship identification logic
- [ ] Created relationship update methods
- [ ] Added retrieval of related documents
- [ ] Tested with various document types
- [ ] Validated bidirectional relationships

---

### Step 5: Create Hierarchical Views

**Estimated time**: 3-4 days

#### Methods to Create

- `DBManager.get_hierarchical_view()` - Generate hierarchical structure
- `DBManager.get_flat_index()` - Retrieve flat index structure

#### Methods to Reuse

- `IndexManager.transform_to_hierarchical()` - Adapt for MongoDB aggregation

#### Testing Criteria

- Hierarchical view matches current JSON structure
- Performance is acceptable for large document sets
- Filtering options work correctly

#### Progress Log

- [ ] Implemented MongoDB aggregation pipeline
- [ ] Created hierarchical view generation
- [ ] Added filtering capabilities
- [ ] Tested with complete document set
- [ ] Validated structure against existing JSON

---

### Step 6: Create Command Line Integration

**Estimated time**: 1-2 days

#### Methods to Create

- `sync_mongodb_from_files()` - CLI command to migrate existing JSON to MongoDB
- `export_mongodb_to_files()` - CLI command to export MongoDB to JSON

#### Testing Criteria

- Migration from JSON to MongoDB works correctly
- Export from MongoDB to JSON creates valid files
- CLI commands have appropriate logging and error handling

#### Progress Log

- [ ] Implemented migration command
- [ ] Implemented export command
- [ ] Added CLI argument parsing
- [ ] Tested migration with existing data
- [ ] Validated exported files

---

### Step 7: Update Querying Functionality

**Estimated time**: 2-3 days

#### Methods to Create

- `DBManager.search_exams(filters)` - Search for exams with filters
- `DBManager.get_exams_by_year(year)` - Get all exams for a year
- `DBManager.get_exams_by_qualification(qualification)` - Get all exams for a qualification

#### Testing Criteria

- Search functionality returns correct results
- Filtering works as expected
- Performance is acceptable for complex queries

#### Progress Log

- [ ] Implemented search functionality
- [ ] Added filtering methods
- [ ] Created specialized retrieval methods
- [ ] Tested with various search criteria
- [ ] Validated result accuracy

---

### Step 8: Create Validation and Error Recovery

**Estimated time**: 2 days

#### Methods to Create

- `DBManager.validate_database()` - Check database integrity
- `DBManager.repair_relationships()` - Fix broken relationships
- `DBManager.sync_with_filesystem()` - Ensure DB and files are in sync

#### Testing Criteria

- Validation identifies inconsistencies
- Repair functions fix common issues
- Sync functionality aligns database with filesystem

#### Progress Log

- [ ] Implemented validation methods
- [ ] Created repair functionality
- [ ] Added synchronization capabilities
- [ ] Tested with intentionally broken data
- [ ] Validated recovery procedures

---

### Step 9: Performance Optimization

**Estimated time**: 2-3 days

#### Methods to Create

- `DBManager.create_indexes()` - Set up appropriate indexes
- `DBManager.get_stats()` - Retrieve database statistics

#### Testing Criteria

- Indexes improve query performance
- Statistics provide useful insights
- Large operations remain performant

#### Progress Log

- [ ] Implemented indexing strategy
- [ ] Created statistics gathering
- [ ] Optimized critical queries
- [ ] Conducted performance testing
- [ ] Documented performance baseline

---

### Step 10: Integration Testing and Documentation

**Estimated time**: 2-3 days

#### Deliverables

- Updated README.md with MongoDB instructions
- Example queries and usage patterns
- Integration tests covering critical paths

#### Testing Criteria

- All integration tests pass
- Documentation is clear and comprehensive
- Example queries work as documented

#### Progress Log

- [ ] Updated project documentation
- [ ] Created example query documentation
- [ ] Implemented integration tests
- [ ] Validated end-to-end workflows
- [ ] Final performance verification

---

## Rollout Strategy

1. Implement in development environment
2. Migrate test dataset to validate functionality
3. Conduct performance testing with production-size dataset
4. Roll out to production with backward compatibility
5. Monitor for issues and performance bottlenecks
6. After stability is confirmed, make MongoDB the primary data store

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| MongoDB performance issues | Low | High | Use appropriate indexes, monitor query performance |
| Data integrity issues | Medium | High | Implement validation, maintain JSON backups |
| Migration errors | Medium | Medium | Create test migrations, verify data integrity |
| Schema evolution challenges | Medium | Medium | Design flexible schema, version documents |
| Connection failures | Low | High | Implement robust error handling and retry logic |

## Dependencies

- MongoDB Atlas account or local MongoDB installation
- PyMongo package
- Environment configuration for connection strings
- Sufficient disk space for indexes and data

## Estimated Timeline

Total implementation time: 3-4 weeks
