# Dashbot Simple Tests

Simple tests that call real APIs to verify functions work correctly.

## Test Structure

- `test_simple.py` - Tests for the main functions you want to verify

## Running Tests

### Install Dependencies
```bash
poetry install
```

### Run All Tests
```bash
pytest tests/test_simple.py
```

### Run Individual Functions
```bash
# Test AI topic generation
pytest tests/test_simple.py::test_generate_topics

# Test topic personalization
pytest tests/test_simple.py::test_personalize_topics

# Test page filtering
pytest tests/test_simple.py::test_get_pages_per_topic

# Test article extraction
pytest tests/test_simple.py::test_extract_article

# Test summary generation
pytest tests/test_simple.py::test_generate_summary
```

### Run Tests Directly (without pytest)
```bash
cd tests
python test_simple.py
```

## What These Tests Do

- **test_generate_topics**: Calls real OpenAI API to generate topics from sample news
- **test_personalize_topics**: Tests sorting topics by importance (no API call)
- **test_get_pages_per_topic**: Tests filtering pages by topic (no API call)  
- **test_extract_article**: Tests newspaper3k article extraction (may fail with fake URL)
- **test_generate_summary**: Calls real OpenAI API to generate summary from sample text

## Environment Variables Needed

Make sure you have these set:
- `OPENAI_API_KEY` - For AI functions
- `GOOGLE_API_KEY` - For search functions (if testing search)
- `GOOGLE_CSE_ID` - For search functions (if testing search)
