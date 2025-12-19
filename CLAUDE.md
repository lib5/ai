# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **FastAPI-based chat API** that integrates with Azure OpenAI GPT-4.1 to provide text and image-based chat functionality with streaming JSON responses. The project includes MCP (Model Context Protocol) client support for ModelScope integration.

## Quick Start Commands

### Development Workflow

```bash
# Install dependencies
pip install -r requirements.txt

# Start the API server
python main.py
# or use the start script
chmod +x start.sh && ./start.sh

# Run tests
python test_chat.py

# Run with custom server URL
python test_chat.py http://your-server:8000

# Run usage examples
python example_usage.py

# Start MCP mock server (optional)
python mock_mcp_server.py --port 3000
```

### Environment Configuration

Create `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Required environment variables:
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint URL
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key
- `AZURE_OPENAI_API_VERSION`: API version (default: 2024-12-01-preview)
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Model deployment name (default: gpt-4.1)
- `MCP_SERVER_URL`: MCP server URL (default: http://localhost:3000)
- `APP_HOST`: Server host (default: 0.0.0.0)
- `APP_PORT`: Server port (default: 8000)

## ReAct Mode (Reasoning and Acting)

The API uses **ReAct mode** by default - an intelligent agent that combines reasoning and tool execution for every request.

### Request Format

```json
{
  "user_id": "user_123",
  "query": [
    {
      "role": "user",
      "content": [
        {"type": "input_text", "text": "搜索关于Python编程的信息"}
      ]
    }
  ]
}
```

### ReAct Flow

1. **Thought**: Agent analyzes the query
2. **Action**: Selects and executes appropriate tools
3. **Observation**: Receives tool results
4. **Repeat**: Continues until answer is complete
5. **Final Answer**: Generates comprehensive response

### Available Tools

- `web_search`: Search for information
- `analyze_image`: Analyze image content
- `search_image`: Search for images
- `get_current_time`: Get current time

### ReAct Response

```json
{
  "data": {
    "react_mode": true,
    "query": "搜索关于Python编程的信息",
    "answer": "最终答案...",
    "reasoning_trace": [
      {
        "iteration": 1,
        "type": "thought",
        "content": "用户询问: Python编程..."
      },
      {
        "iteration": 1,
        "type": "action",
        "content": {"tool": "web_search", "arguments": {...}}
      },
      {
        "iteration": 1,
        "type": "observation",
        "content": {"tool": "web_search", "result": {...}}
      }
    ],
    "iterations": 1,
    "steps": [...]
  }
}
```

### Testing ReAct

```bash
# Test ReAct mode (text)
python test_react_simple.py

# Test ReAct with image
python test_react_image.py
```

All requests automatically use ReAct mode - no additional flags needed!

## Code Architecture

### High-Level Structure

```
chatapi/
├── main.py                      # FastAPI application entry point
├── config.py                    # Configuration management (Settings class)
├── services/                    # Service layer modules
│   ├── azure_openai_service.py # Azure OpenAI API client
│   ├── streaming_service.py    # Streaming response handling
│   ├── mcp_client.py           # MCP protocol client
│   └── react_agent.py          # ReAct Agent for reasoning and acting
├── test_chat.py                # Comprehensive test suite
├── example_usage.py            # Usage examples and demos
├── test_react_simple.py        # Simple ReAct mode test
├── test_react_image.py         # ReAct + image analysis test
├── mock_mcp_server.py          # Mock MCP server for testing
├── start.sh                    # Application startup script
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variable template
└── README.md                  # Detailed documentation
```

### Architecture Patterns

**1. Service-Oriented Design**
- Each external integration is encapsulated in a service class within `/services/`
- `AzureOpenAIService`: Handles Azure OpenAI API communication
- `StreamingService`: Manages streaming JSON responses
- `MCPClient`: Provides MCP protocol client functionality

**2. Async/Await Throughout**
- All API endpoints use asynchronous handlers
- All service methods are async
- Uses `aiohttp` for HTTP client operations

**3. Step-by-Step Processing**
The chat endpoint (`/api/chat`) processes requests in distinct steps:
1. **System**: Request initiation
2. **InputParser**: Parse text and image inputs
3. **AzureOpenAI**: Call Azure OpenAI API
4. **ResponseGenerator**: Format final response
5. **Finish**: Complete processing

Each step is tracked with:
- `message_id`: Unique identifier
- `present_content`: Human-readable description
- `tool_type`: Component type
- `parameters`: JSON string of parameters
- `tool_status`: Current status
- `observation`: Result or error message
- `execution_duration`: Processing time in milliseconds

**4. ReAct Agent Pattern**
When `react_mode: true`, the API uses a ReAct agent that:
1. **Thinks**: Analyzes the query and determines what action to take
2. **Acts**: Executes appropriate tools from the tool registry
3. **Observes**: Receives and processes tool results
4. **Repeats**: Continues the loop until sufficient information is gathered
5. **Answers**: Generates a comprehensive final response

The agent maintains a reasoning trace showing each step of the process.

**4. Streaming Response Format**
The API returns data as Server-Sent Events (SSE):
- `event: start` - Response initiation
- `event: chunk` - Data chunks with sequence numbers
- `event: end` - Completion with total length

## Key Components

### main.py (FastAPI Application)

**Main Endpoints:**
- `POST /api/chat`: Core chat functionality with text/image support
- `GET /health`: Health check endpoint

**Request Format:**
```python
{
  "user_id": "string",
  "query": [
    {
      "role": "user",
      "content": [
        {"type": "input_text", "text": "..."},
        {"type": "input_image", "image_url": "data:image/jpeg;base64,..."}
      ]
    }
  ]
}
```

**Response Format:**
```python
{
  "code": 200,
  "message": "成功",
  "timestamp": "ISO8601",
  "requestId": "req_xxx",
  "data": {
    "react_mode": true,
    "query": "用户查询",
    "answer": "最终答案",
    "reasoning_trace": [
      {"iteration": 1, "type": "thought", "content": "..."},
      {"iteration": 1, "type": "action", "content": {...}},
      {"iteration": 1, "type": "observation", "content": {...}}
    ],
    "iterations": 1,
    "steps": [ProcessingStep...]
  }
}
```

### services/azure_openai_service.py

- **Primary class**: `AzureOpenAIService`
- **Key methods**:
  - `chat_completion()`: Standard API call
  - `chat_completion_stream()`: Streamed API responses
- Uses `aiohttp.ClientSession` for async HTTP requests
- Constructs Azure OpenAI API URLs with deployment names
- Returns parsed JSON responses

### services/streaming_service.py

- **Primary class**: `StreamingService`
- **Key methods**:
  - `generate_stream()`: Convert JSON to streaming chunks
  - `generate_stream_with_steps()`: Stream step-by-step updates
- Sends SSE-formatted data with configurable chunk sizes
- Adds artificial delays to simulate streaming

### services/mcp_client.py

- **Base class**: `MCPClient` for general MCP protocol
- **Derived class**: `ModelscopeMCPClient` for ModelScope-specific operations
- **Key methods**:
  - `list_tools()`: Enumerate available MCP tools
  - `call_tool()`: Invoke MCP tool with arguments
  - `search_model()`: ModelScope model search
  - `get_model_info()`: Retrieve model details

### services/react_agent.py

- **Primary class**: `ReActAgent` for reasoning and acting
- **Key methods**:
  - `run()`: Main ReAct loop (think -> act -> observe -> repeat)
  - `think()`: Generate reasoning for the query
  - `act()`: Execute tools from registry
- **Tool class**: Defines available tools with name, description, and function
- **Built-in tools**:
  - `web_search`: Search for information
  - `analyze_image`: Analyze image content
  - `search_image`: Search for images
  - `get_current_time`: Get current time
- **Returns**: Complete reasoning trace + final answer

## Testing Strategy

### test_chat.py

Comprehensive test suite covering:
1. **Pure text input** - Basic chat functionality
2. **Text + image input** - Multimodal processing
3. **Multiple queries** - Multi-turn conversations
4. **Streaming responses** - Real-time data handling
5. **Health checks** - Service availability
6. **MCP client** - External service integration

Run all tests:
```bash
python test_chat.py
```

Run against remote server:
```bash
python test_chat.py http://server:8000
```

### test_react_simple.py

Simple test for ReAct mode functionality:
- Tests text-based ReAct queries
- Verifies reasoning trace generation
- Shows thought -> action -> observation flow

Run test:
```bash
python test_react_simple.py
```

### test_react_image.py

Test ReAct mode with image analysis:
- Tests ReAct with multimodal input
- Verifies image processing in reasoning loop
- Shows tool selection for image queries

Run test:
```bash
python test_react_image.py
```

### example_usage.py

Demonstrates practical usage patterns:
1. Text-only conversations
2. Multimodal input (text + image)
3. Multi-turn dialogues
4. Streaming response handling
5. Error scenarios
6. Health check monitoring

Run all examples:
```bash
python example_usage.py
```

## Dependencies

Key packages in `requirements.txt`:
- `fastapi==0.104.1` - Web framework
- `uvicorn[standard]==0.24.0` - ASGI server
- `aiohttp==3.9.1` - Async HTTP client/server
- `pydantic==2.5.0` - Data validation
- `python-multipart==0.0.6` - Multipart form handling

## Configuration Details

### config.py

- **Settings class**: Manages all configuration from environment variables
- **Validation**: Checks required Azure OpenAI parameters on initialization
- **Default values**: Provides sensible defaults for optional parameters

### Environment Variables Priority

1. Explicit `.env` file values
2. System environment variables
3. Hardcoded defaults in `Settings` class

## API Contract

### Success Response (200)
```json
{
  "code": 200,
  "message": "成功",
  "timestamp": "2025-12-16T10:30:00.000Z",
  "requestId": "req_5f8c9a2b3d1e",
  "data": {
    "steps": [...]
  }
}
```

### Error Response (500)
```json
{
  "code": 500,
  "message": "处理请求时发生错误",
  "timestamp": "2025-12-16T10:30:00.000Z",
  "requestId": "req_xxx",
  "data": {
    "steps": [
      {
        "tool_status": "Error",
        "observation": "Error details..."
      }
    ]
  }
}
```

### Health Check Response (200)
```json
{
  "status": "healthy",
  "timestamp": "2025-12-16T10:30:00.000Z"
}
```

## Development Notes

### CORS Configuration
- Enabled with `allow_origins=["*"]` for development
- Allows all methods and headers
- Consider restricting in production

### Image Handling
- Supports base64-encoded images only
- Must start with `data:image/{format};base64,`
- Validates format before processing
- Raises HTTP 400 for invalid formats

### Async Patterns
- All I/O operations use `async/await`
- Uses `asyncio.get_event_loop().time()` for duration tracking
- Proper session management with context managers
- Error handling preserves async context

### Error Handling Strategy
- Try/catch blocks wrap critical operations
- Errors logged as processing steps
- HTTP exceptions raised for client errors
- Generic 500 responses for server errors

## Important Files to Reference

- **README.md**: Complete documentation with examples
- **config.py:20-28**: Configuration validation logic
- **main.py:56-217**: Main chat endpoint implementation
- **services/azure_openai_service.py:22-66**: Azure OpenAI API integration
- **test_chat.py:26-168**: Test cases and scenarios
- **example_usage.py:14-241**: Usage patterns and best practices

## Common Development Tasks

### Adding a New Endpoint
1. Define Pydantic models in `main.py`
2. Add endpoint handler with `@app.post()` or `@app.get()`
3. Follow step-by-step processing pattern
4. Add corresponding tests in `test_chat.py`
5. Document in README.md

### Modifying Azure OpenAI Integration
1. Update `services/azure_openai_service.py`
2. Adjust API version in `config.py` if needed
3. Test with `test_chat.py` and `example_usage.py`
4. Verify streaming and non-streaming modes

### Extending MCP Client
1. Add methods to `ModelscopeMCPClient` in `services/mcp_client.py`
2. Follow existing async patterns
3. Add tests in `test_chat.py:test_modelscope_mcp()`
4. Update examples in `example_usage.py`

## Production Considerations

- Configure proper CORS origins instead of wildcard
- Add request rate limiting
- Implement proper logging (currently minimal)
- Add request authentication/authorization
- Set up monitoring for Azure OpenAI API usage
- Configure proper error tracking
- Add request/response size limits
- Implement circuit breaker for external services
