# Neuropetitorius AI Tutor API Documentation

**Version:** 1.0  
**Last Updated:** April 2026

---

## Overview

The Neuropetitorius AI Tutor API provides programmatic access to our AI-powered educational platform. Partners can ingest educational content, create tutoring sessions, and interact with an AI tutor that responds contextually based on the provided material.

### Base URL

```
http://localhost:8000  (development)
https://api.neuropetitorius.com  (production)
```

### Authentication

All API requests require authentication via a Bearer token. Include the `Authorization` header in every request:

```http
Authorization: Bearer <your_api_key>
```

---

## Endpoints

### 1. Content Ingestion

Ingest educational content into the system. Content can be provided as text or uploaded as a file.

**Endpoint:** `POST /v1/content/ingest`

**Content-Type:** `multipart/form-data`

| Parameter | Type | Required | Constraints | Description |
|-----------|------|----------|-------------|-------------|
| `topic_id` | string | Yes | max 256 chars | Unique identifier for the topic |
| `title` | string | Yes | max 512 chars | Title of the content |
| `subject` | string | No | max 64 chars | Subject category |
| `language` | string | No | max 10 chars | Content language (default: `lt`) |
| `content` | string | No | min 10 chars, max 500,000 chars | Text content |
| `file` | file | No | PDF, DOCX, XLSX, TXT, JPG, PNG | File upload |

**Response:**

```json
{
  "topic_id": "string",
  "content_item_id": "string",
  "chunks_created": "number",
  "tokens_embedded": "number",
  "content_changed": "boolean",
  "file_processed": "boolean"
}
```

**Curl Example:**

```bash
curl -X POST http://localhost:8000/v1/content/ingest \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "topic_id=math-algebra-101" \
  -F "title=Introduction to Algebra" \
  -F "subject=Mathematics" \
  -F "language=lt" \
  -F "content=Algebra is a branch of mathematics..." \
  -F "file=@/path/to/document.pdf"
```

---

### 2. Delete Content

Remove all content associated with a specific topic.

**Endpoint:** `DELETE /v1/content/{topic_id}`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `topic_id` | string | The unique identifier of the topic to delete |

**Response:**

```json
{
  "message": "Content deleted successfully"
}
```

**Curl Example:**

```bash
curl -X DELETE http://localhost:8000/v1/content/math-algebra-101 \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 3. Create Session

Create a new tutoring session for a student.

**Endpoint:** `POST /v1/sessions`

**Content-Type:** `application/json`

**Request Body:**

```json
{
  "topic_id": "string",
  "student_external_id": "string",
  "title": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `topic_id` | string | Yes | Associated topic ID |
| `student_external_id` | string | Yes | External student identifier |
| `title` | string | Yes | Session title |

**Response:**

```json
{
  "session_id": "string",
  "topic_id": "string",
  "language": "string",
  "created_at": "datetime"
}
```

**Curl Example:**

```bash
curl -X POST http://localhost:8000/v1/sessions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "topic_id": "math-algebra-101",
    "student_external_id": "student-12345",
    "title": "Algebra Practice Session"
  }'
```

---

### 4. Get Session

Retrieve session details including message history.

**Endpoint:** `GET /v1/sessions/{session_id}`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | The session ID |

**Response:**

```json
{
  "session_id": "string",
  "topic_id": "string",
  "language": "string",
  "title": "string",
  "created_at": "datetime",
  "messages": [
    {
      "message_id": "string",
      "role": "student|assistant",
      "content": "string",
      "created_at": "datetime"
    }
  ]
}
```

**Curl Example:**

```bash
curl -X GET http://localhost:8000/v1/sessions/session-abc123 \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 5. Delete Session

Delete a tutoring session and its associated messages.

**Endpoint:** `DELETE /v1/sessions/{session_id}`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | The session ID to delete |

**Response:**

```json
{
  "message": "Session deleted successfully"
}
```

**Curl Example:**

```bash
curl -X DELETE http://localhost:8000/v1/sessions/session-abc123 \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### 6. Send Message (AI Tutor)

Send a message to the AI tutor and receive a contextual response. This endpoint supports Server-Sent Events (SSE) for streaming responses.

**Endpoint:** `POST /v1/sessions/{session_id}/messages`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | The session ID |

**Content-Type:** `application/json`

**Request Body:**

```json
{
  "content": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | Student's message to the tutor |

**Response:**

```json
{
  "message_id": "string",
  "content": "string",
  "role": "assistant",
  "created_at": "datetime"
}
```

**Streaming Response (SSE):**

For streaming responses, the endpoint returns Server-Sent Events format:

```
data: {"content": "The", "done": false}
data: {"content": " AI ", "done": false}
data: {"content": "tutor", "done": false}
data: {"content": " response", "done": false}
data: {"content": "...", "done": true}
```

To receive streaming responses, include the `Accept: text/event-stream` header.

**Curl Example (Standard):**

```bash
curl -X POST http://localhost:8000/v1/sessions/session-abc123/messages \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Can you explain how to solve quadratic equations?"
  }'
```

**Curl Example (Streaming):**

```bash
curl -X POST http://localhost:8000/v1/sessions/session-abc123/messages \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "content": "Can you explain how to solve quadratic equations?"
  }'
```

---

### 7. Health Check

Check the API service status.

**Endpoint:** `GET /v1/health`

**Response:**

```json
{
  "status": "ok"
}
```

**Curl Example:**

```bash
curl -X GET http://localhost:8000/v1/health
```

---

## Error Codes

The API uses standard HTTP status codes. Error responses include a code and message:

| Status Code | Error Code | Description |
|-------------|------------|-------------|
| 400 | `VALIDATION_ERROR` | Request validation failed |
| 401 | `INVALID_API_KEY` | The provided API key is invalid |
| 401 | `MISSING_AUTH` | Authorization header is missing |
| 401 | `PARTNER_INACTIVE` | Partner account is inactive |
| 404 | `NOT_FOUND` | Resource not found |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Internal server error |

**Error Response Format:**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "topic_id is required"
  }
}
```

---

## Rate Limits

Default rate limit: **60 requests per minute per partner**

When rate limited, the API responds with:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later."
  }
}
```

---

## SSE Format for Streaming

The AI Tutor message endpoint supports Server-Sent Events (SSE) for real-time streaming responses.

### Event Structure

Each event is a JSON object prefixed with `data: `:

```
data: {"content": "partial", "done": false}
data: {"content": " response", "done": false}
data: {"done": true}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `content` | string | Chunk of the response content |
| `done` | boolean | Indicates if this is the final chunk |

### Client Implementation Example

```javascript
const response = await fetch('/v1/sessions/{session_id}/messages', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream'
  },
  body: JSON.stringify({ content: 'Your message' })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      if (data.content) process.stdout.write(data.content);
      if (data.done) console.log('\n-stream complete-');
    }
  }
}
```

---

## Best Practices

1. **Secure Your API Key** - Never expose your API key in client-side code
2. **Handle Errors Gracefully** - Implement retry logic for transient errors
3. **Use Streaming for Long Responses** - Enable SSE for better UX with longer AI responses
4. **Validate Input** - Check request parameters before sending
5. **Monitor Rate Limits** - Implement request throttling in your application

---

## Support

For API support and inquiries:
- **Email:** api-support@neuropetitorius.com
- **Documentation:** https://docs.neuropetitorius.com
- **Status Page:** https://status.neuropetitorius.com

---

*Neuropetitorius AI Tutor API &copy; 2026. All rights reserved.*
