# Neuropetitorius Integration Guide

## Integrate Neuropetitorius AI Tutor in 1 Hour

This guide walks you through integrating Neuropetitorius into your platform in under 5 minutes. You'll go from zero to your first AI tutoring session.

---

## Quick Start (5 Steps in 5 Minutes)

### Step 1: Get Your API Key

Contact Neuropetitorius to obtain your API key. The format is `npk_...`

Example key: `npk_abc123def456`

### Step 2: Upload Your First Lesson Content

```bash
# Using curl
curl -X POST http://localhost:8000/v1/content/ingest \
  -H "Authorization: Bearer npk_abc123def456" \
  -F "topic_id=math-algebra-101" \
  -F "title=Introduction to Algebra" \
  -F "subject=Mathematics" \
  -F "language=lt" \
  -F "content=Algebra is a branch of mathematics that deals with symbols and rules for manipulating those symbols. It is a unifying thread of almost all of mathematics and includes everything from solving elementary equations to studying abstractions such as groups, rings, and fields.

The basic operations in algebra are addition, subtraction, multiplication, and division. For example, if we have the equation x + 5 = 10, we can solve for x by subtracting 5 from both sides: x = 5.

Quadratic equations are equations of the form ax^2 + bx + c = 0, where a, b, and c are constants. The solutions can be found using the quadratic formula: x = (-b ± sqrt(b^2 - 4ac)) / 2a."

# Expected response:
# {
#   "topic_id": "math-algebra-101",
#   "content_item_id": "content-abc123",
#   "chunks_created": 3,
#   "tokens_embedded": 450,
#   "content_changed": true,
#   "file_processed": false
# }
```

### Step 3: Create a Tutoring Session

```bash
curl -X POST http://localhost:8000/v1/sessions \
  -H "Authorization: Bearer npk_abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "topic_id": "math-algebra-101",
    "student_external_id": "student-001",
    "title": "Algebra Practice Session"
  }'

# Expected response:
# {
#   "session_id": "session-xyz789",
#   "topic_id": "math-algebra-101",
#   "language": "lt",
#   "created_at": "2026-04-07T10:30:00Z"
# }
```

### Step 4: Send a Student Message

```bash
curl -X POST http://localhost:8000/v1/sessions/session-xyz789/messages \
  -H "Authorization: Bearer npk_abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Kaip spręsti kvadratinę lygtį?"
  }'

# Expected response:
# {
#   "message_id": "msg-123",
#   "content": "Norėdami išspręsti kvadratinę lygtį ax² + bx + c = 0, naudokite kvadratinę formulę: x = (-b ± √(b² - 4ac)) / 2a. Pirmiausia apskaičiuokite diskriminantą b² - 4ac.",
#   "role": "assistant",
#   "created_at": "2026-04-07T10:30:05Z"
# }
```

### Step 5: Receive AI Tutor Response

That's it! The AI tutor automatically responds based on the lesson content you uploaded. The response is contextual and in the same language as the content.

---

## Prerequisites

- **Python 3.12+** or **Node.js 18+**
- An API key from Neuropetitorius (format: `npk_...`)
- Base URL: `http://localhost:8000` (development) or `https://api.neuropetitorius.com` (production)

---

## Detailed Integration

### Step 1: Get Your API Key

Contact Neuropetitorius to get your API key. Format: `npk_...`

Your API key authenticates all API requests. Keep it secure!

---

### Step 2: Upload Content

The content ingestion endpoint processes your educational material and stores it for the AI tutor to reference.

**Endpoint:** `POST /v1/content/ingest`

#### Python Example

```python
import requests

API_KEY = "npk_abc123def456"
BASE_URL = "http://localhost:8000"  # Change to production URL in live environment

def upload_content(topic_id: str, title: str, content: str, subject: str = None, language: str = "lt"):
    """Upload lesson content to Neuropetitorius"""
    url = f"{BASE_URL}/v1/content/ingest"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    data = {
        "topic_id": topic_id,
        "title": title,
        "content": content,
        "subject": subject,
        "language": language
    }
    
    response = requests.post(url, data=data, headers=headers)
    response.raise_for_status()
    return response.json()

# Example usage with Lithuanian math content
result = upload_content(
    topic_id="math-algebra-101",
    title="Introduction to Algebra",
    subject="Mathematics",
    language="lt",
    content="""Algebra is a branch of mathematics that deals with symbols and rules for manipulating those symbols.
    
The basic operations in algebra are addition, subtraction, multiplication, and division.
For example, if we have the equation x + 5 = 10, we can solve for x by subtracting 5 from both sides: x = 5.

Quadratic equations are equations of the form ax^2 + bx + c = 0, where a, b, and c are constants.
The solutions can be found using the quadratic formula: x = (-b ± sqrt(b^2 - 4ac)) / 2a."""
)

print(f"Content uploaded! Chunks created: {result['chunks_created']}")
```

#### JavaScript/TypeScript Example

```javascript
const API_KEY = "npk_abc123def456";
const BASE_URL = "http://localhost:8000"; // Change to production URL in live environment

async function uploadContent(topicId, title, content, subject = null, language = "lt") {
  const url = `${BASE_URL}/v1/content/ingest`;
  
  const formData = new FormData();
  formData.append("topic_id", topicId);
  formData.append("title", title);
  formData.append("content", content);
  formData.append("subject", subject);
  formData.append("language", language);

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${API_KEY}`
    },
    body: formData
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.statusText}`);
  }

  return response.json();
}

// Example usage
const result = await uploadContent(
  "math-algebra-101",
  "Introduction to Algebra",
  `Algebra is a branch of mathematics that deals with symbols and rules for manipulating those symbols.

The basic operations in algebra are addition, subtraction, multiplication, and division.
For example, if we have the equation x + 5 = 10, we can solve for x by subtracting 5 from both sides: x = 5.

Quadratic equations are equations of the form ax^2 + bx + c = 0, where a, b, and c are constants.
The solutions can be found using the quadratic formula: x = (-b ± sqrt(b^2 - 4ac)) / 2a.`,
  "Mathematics",
  "lt"
);

console.log(`Content uploaded! Chunks created: ${result.chunks_created}`);
```

#### curl Example

```bash
curl -X POST http://localhost:8000/v1/content/ingest \
  -H "Authorization: Bearer npk_abc123def456" \
  -F "topic_id=math-algebra-101" \
  -F "title=Introduction to Algebra" \
  -F "subject=Mathematics" \
  -F "language=lt" \
  -F "content=Algebra is a branch of mathematics..."
```

#### Lithuanian Math Example Content

```text
Algebra yra matematikos šaka, dirbanti su simboliais ir taisyklėmis, kaip su jais elgtis.
Ji yra vientisa beveik visos matematikos gija ir apima viską nuo elementarių lygčių sprendimo iki tokių abstrakcijų kaip grupės, žiedai ir laukai.

Pagrindinės algebrao operacijos yra sudėtis, atimtis, daugyba ir dalyba.
Pavyzdžiui, jei turime lygtį x + 5 = 10, galime išspręsti x atimdami 5 iš abiejų pusių: x = 5.

Kvadratinės lygtys yra lygtys forma ax² + bx + c = 0, kur a, b, c yra konstantos.
Sprendimus galima rasti naudojant kvadratinę formulę: x = (-b ± √(b² - 4ac)) / 2a.
```

---

### Step 3: Create a Session

Sessions track individual student tutoring conversations.

**Endpoint:** `POST /v1/sessions`

#### Python Example

```python
def create_session(topic_id: str, student_external_id: str, title: str):
    """Create a new tutoring session for a student"""
    url = f"{BASE_URL}/v1/sessions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "topic_id": topic_id,
        "student_external_id": student_external_id,
        "title": title
    }
    
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

# Create a session
session = create_session(
    topic_id="math-algebra-101",
    student_external_id="student-001",
    title="Algebra Practice Session"
)

session_id = session["session_id"]
print(f"Session created: {session_id}")
```

#### JavaScript Example

```javascript
async function createSession(topicId, studentExternalId, title) {
  const response = await fetch(`${BASE_URL}/v1/sessions`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${API_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      topic_id: topicId,
      student_external_id: studentExternalId,
      title: title
    })
  });
  
  return response.json();
}

const session = await createSession(
  "math-algebra-101",
  "student-001",
  "Algebra Practice Session"
);

console.log(`Session created: ${session.session_id}`);
```

#### curl Example

```bash
curl -X POST http://localhost:8000/v1/sessions \
  -H "Authorization: Bearer npk_abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "topic_id": "math-algebra-101",
    "student_external_id": "student-001",
    "title": "Algebra Practice Session"
  }'
```

---

### Step 4: Chat with the AI Tutor

Send messages and receive AI-generated responses based on your content.

**Endpoint:** `POST /v1/sessions/{session_id}/messages`

#### Python Example (Standard)

```python
def send_message(session_id: str, content: str):
    """Send a message to the AI tutor"""
    url = f"{BASE_URL}/v1/sessions/{session_id}/messages"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {"content": content}
    
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

# Send a message (in Lithuanian)
response = send_message(session_id, "Kaip spręsti kvadratinę lygtį?")

print(f"AI Tutor: {response['content']}")
```

#### Python Example (Streaming with SSE)

```python
import requests
import json

def stream_message(session_id: str, content: str):
    """Send a message and stream the AI tutor response"""
    url = f"{BASE_URL}/v1/sessions/{session_id}/messages"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    data = {"content": content}
    
    with requests.post(url, json=data, headers=headers, stream=True) as response:
        response.raise_for_status()
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    json_str = line[6:]  # Remove "data: " prefix
                    if json_str.strip():
                        chunk = json.loads(json_str)
                        if chunk.get("content"):
                            full_response += chunk["content"]
                            print(chunk["content"], end="", flush=True)
                        if chunk.get("done"):
                            print("\n[Stream complete]")
        return full_response

# Stream a response
print("AI Tutor: ", end="")
response_text = stream_message(session_id, "Paaiškink man kvadratines lygtis paprastai")
```

#### JavaScript Example

```javascript
async function sendMessage(sessionId, content) {
  const response = await fetch(`${BASE_URL}/v1/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${API_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ content })
  });
  
  return response.json();
}

// Send a message
const response = await sendMessage(session.session_id, "Kaip spręsti kvadratinę lygtį?");
console.log(`AI Tutor: ${response.content}`);
```

#### JavaScript Example (Streaming)

```javascript
async function streamMessage(sessionId, content) {
  const response = await fetch(`${BASE_URL}/v1/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${API_KEY}`,
      "Content-Type": "application/json",
      "Accept": "text/event-stream"
    },
    body: JSON.stringify({ content })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let fullResponse = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        if (data.content) {
          process.stdout.write(data.content);
          fullResponse += data.content;
        }
        if (data.done) {
          console.log('\n[Stream complete]');
        }
      }
    }
  }
  
  return fullResponse;
}

// Stream a response
process.stdout.write("AI Tutor: ");
await streamMessage(session.session_id, "Paaiškink man kvadratines lygtis paprastai");
```

#### curl Example (Standard)

```bash
curl -X POST http://localhost:8000/v1/sessions/session-xyz789/messages \
  -H "Authorization: Bearer npk_abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Kaip spręsti kvadratinę lygtį?"
  }'
```

#### curl Example (Streaming)

```bash
curl -X POST http://localhost:8000/v1/sessions/session-xyz789/messages \
  -H "Authorization: Bearer npk_abc123def456" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "content": "Kaip spręsti kvadratinę lygtį?"
  }'
```

---

## Full Code Examples

### Complete Python Example

```python
import requests

# Configuration
API_KEY = "npk_abc123def456"
BASE_URL = "http://localhost:8000"  # Production: https://api.neuropetitorius.com

class NeuropetitoriusClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def upload_content(self, topic_id: str, title: str, content: str, 
                       subject: str = None, language: str = "lt") -> dict:
        """Upload lesson content"""
        url = f"{self.base_url}/v1/content/ingest"
        data = {
            "topic_id": topic_id,
            "title": title,
            "content": content,
            "subject": subject,
            "language": language
        }
        response = self.session.post(url, data=data)
        response.raise_for_status()
        return response.json()
    
    def create_session(self, topic_id: str, student_external_id: str, 
                       title: str) -> dict:
        """Create a tutoring session"""
        url = f"{self.base_url}/v1/sessions"
        response = self.session.post(url, json={
            "topic_id": topic_id,
            "student_external_id": student_external_id,
            "title": title
        })
        response.raise_for_status()
        return response.json()
    
    def send_message(self, session_id: str, content: str) -> dict:
        """Send a message to the AI tutor"""
        url = f"{self.base_url}/v1/sessions/{session_id}/messages"
        response = self.session.post(url, json={"content": content})
        response.raise_for_status()
        return response.json()
    
    def delete_content(self, topic_id: str) -> dict:
        """Delete content for a topic"""
        url = f"{self.base_url}/v1/content/{topic_id}"
        response = self.session.delete(url)
        response.raise_for_status()
        return response.json()
    
    def delete_session(self, session_id: str) -> dict:
        """Delete a session"""
        url = f"{self.base_url}/v1/sessions/{session_id}"
        response = self.session.delete(url)
        response.raise_for_status()
        return response.json()


# Full integration example
def main():
    client = NeuropetitoriusClient(API_KEY, BASE_URL)
    
    # Step 1: Upload content
    print("Step 1: Uploading content...")
    content_result = client.upload_content(
        topic_id="math-algebra-101",
        title="Introduction to Algebra",
        subject="Mathematics",
        language="lt",
        content="""Algebra is a branch of mathematics that deals with symbols and rules for manipulating those symbols.
        
The basic operations in algebra are addition, subtraction, multiplication, and division.
For example, if we have the equation x + 5 = 10, we can solve for x by subtracting 5 from both sides: x = 5.

Quadratic equations are equations of the form ax^2 + bx + c = 0, where a, b, and c are constants.
The solutions can be found using the quadratic formula: x = (-b ± sqrt(b^2 - 4ac)) / 2a."""
    )
    print(f"  Content uploaded! {content_result['chunks_created']} chunks created")
    
    # Step 2: Create session
    print("\nStep 2: Creating session...")
    session = client.create_session(
        topic_id="math-algebra-101",
        student_external_id="student-001",
        title="Algebra Practice Session"
    )
    session_id = session["session_id"]
    print(f"  Session created: {session_id}")
    
    # Step 3: Chat with AI tutor
    print("\nStep 3: Sending message to AI tutor...")
    response = client.send_message(session_id, "Kaip spręsti kvadratinę lygtį?")
    print(f"  AI Tutor: {response['content']}")
    
    print("\n✓ Integration complete!")


if __name__ == "__main__":
    main()
```

### Complete JavaScript Example (Web Integration)

```javascript
const API_KEY = "npk_abc123def456";
const BASE_URL = "http://localhost:8000"; // Production: https://api.neuropetitorius.com

class NeuropetitoriusClient {
  constructor(apiKey, baseUrl) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }

  getHeaders() {
    return {
      "Authorization": `Bearer ${this.apiKey}`
    };
  }

  async uploadContent(topicId, title, content, subject = null, language = "lt") {
    const formData = new FormData();
    formData.append("topic_id", topicId);
    formData.append("title", title);
    formData.append("content", content);
    formData.append("subject", subject);
    formData.append("language", language);

    const response = await fetch(`${this.baseUrl}/v1/content/ingest`, {
      method: "POST",
      headers: this.getHeaders(),
      body: formData
    });
    
    if (!response.ok) throw new Error(`Upload failed: ${response.statusText}`);
    return response.json();
  }

  async createSession(topicId, studentExternalId, title) {
    const response = await fetch(`${this.baseUrl}/v1/sessions`, {
      method: "POST",
      headers: {
        ...this.getHeaders(),
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        topic_id: topicId,
        student_external_id: studentExternalId,
        title: title
      })
    });
    
    return response.json();
  }

  async sendMessage(sessionId, content) {
    const response = await fetch(`${this.baseUrl}/v1/sessions/${sessionId}/messages`, {
      method: "POST",
      headers: {
        ...this.getHeaders(),
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ content })
    });
    
    return response.json();
  }

  async *streamMessage(sessionId, content) {
    const response = await fetch(`${this.baseUrl}/v1/sessions/${sessionId}/messages`, {
      method: "POST",
      headers: {
        ...this.getHeaders(),
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
      },
      body: JSON.stringify({ content })
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
          if (data.content || data.done) {
            yield data;
          }
        }
      }
    }
  }

  async deleteContent(topicId) {
    const response = await fetch(`${this.baseUrl}/v1/content/${topicId}`, {
      method: "DELETE",
      headers: this.getHeaders()
    });
    return response.json();
  }

  async deleteSession(sessionId) {
    const response = await fetch(`${this.baseUrl}/v1/sessions/${sessionId}`, {
      method: "DELETE",
      headers: this.getHeaders()
    });
    return response.json();
  }
}

// Example usage in a web application
async function main() {
  const client = new NeuropetitoriusClient(API_KEY, BASE_URL);

  // Step 1: Upload content
  console.log("Step 1: Uploading content...");
  const contentResult = await client.uploadContent(
    "math-algebra-101",
    "Introduction to Algebra",
    `Algebra is a branch of mathematics that deals with symbols and rules for manipulating those symbols.
    
The basic operations in algebra are addition, subtraction, multiplication, and division.
For example, if we have the equation x + 5 = 10, we can solve for x by subtracting 5 from both sides: x = 5.

Quadratic equations are equations of the form ax^2 + bx + c = 0, where a, b, and c are constants.
The solutions can be found using the quadratic formula: x = (-b ± sqrt(b^2 - 4ac)) / 2a.`,
    "Mathematics",
    "lt"
  );
  console.log(`  Content uploaded! ${contentResult.chunks_created} chunks created`);

  // Step 2: Create session
  console.log("\nStep 2: Creating session...");
  const session = await client.createSession(
    "math-algebra-101",
    "student-001",
    "Algebra Practice Session"
  );
  console.log(`  Session created: ${session.session_id}`);

  // Step 3: Chat with AI tutor
  console.log("\nStep 3: Sending message to AI tutor...");
  const response = await client.sendMessage(session.session_id, "Kaip spręsti kvadratinę lygtį?");
  console.log(`  AI Tutor: ${response.content}`);

  console.log("\n✓ Integration complete!");
}

// Run the example
main().catch(console.error);
```

---

## Testing Your Integration

### Verify Your Setup

1. **Check API Health**
   ```bash
   curl http://localhost:8000/v1/health
   # Expected: {"status": "ok"}
   ```

2. **Test Authentication**
   ```bash
   # Should succeed with valid key
   curl -X POST http://localhost:8000/v1/sessions \
     -H "Authorization: Bearer npk_abc123def456" \
     -H "Content-Type: application/json" \
     -d '{"topic_id":"test","student_external_id":"test","title":"test"}'
   
   # Should fail without key
   curl -X POST http://localhost:8000/v1/sessions \
     -H "Content-Type: application/json" \
     -d '{"topic_id":"test","student_external_id":"test","title":"test"}'
   # Expected: 401 with error code MISSING_AUTH
   ```

3. **Test Full Flow**
   - Upload content → Create session → Send message → Receive response

### Common Issues and Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `401 INVALID_API_KEY` | Invalid or expired API key | Verify your API key format starts with `npk_` |
| `401 MISSING_AUTH` | No Authorization header | Add `Authorization: Bearer <key>` header |
| `404 NOT_FOUND` | Invalid topic_id or session_id | Check that the topic exists before creating session |
| `429 RATE_LIMIT_EXCEEDED` | Too many requests | Implement request throttling (60 req/min default) |
| `400 VALIDATION_ERROR` | Missing required field | Check required fields for each endpoint |
| Empty AI responses | Content not indexed properly | Verify content upload returned `chunks_created > 0` |

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "topic_id is required"
  }
}
```

---

## Advanced Features

### File Upload Support

Upload PDF, DOCX, XLSX, TXT, JPG, or PNG files for content ingestion.

**Python:**
```python
def upload_file(topic_id: str, title: str, file_path: str, subject: str = None):
    """Upload a file as lesson content"""
    url = f"{BASE_URL}/v1/content/ingest"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {
            "topic_id": topic_id,
            "title": title,
            "subject": subject
        }
        response = requests.post(url, data=data, files=files, headers=headers)
    
    return response.json()

# Upload a PDF
result = upload_file(
    topic_id="math-algebra-101",
    title="Algebra Textbook Chapter 1",
    file_path="./content/algebra-chapter1.pdf",
    subject="Mathematics"
)
```

**curl:**
```bash
curl -X POST http://localhost:8000/v1/content/ingest \
  -H "Authorization: Bearer npk_abc123def456" \
  -F "topic_id=math-algebra-101" \
  -F "title=Algebra Textbook Chapter 1" \
  -F "subject=Mathematics" \
  -F "file=@/path/to/algebra-chapter1.pdf"
```

### Session Management

```python
# Get session details including message history
def get_session(session_id: str):
    url = f"{BASE_URL}/v1/sessions/{session_id}"
    response = requests.get(url, headers={"Authorization": f"Bearer {API_KEY}"})
    return response.json()

# Delete a session
def delete_session(session_id: str):
    url = f"{BASE_URL}/v1/sessions/{session_id}"
    response = requests.delete(url, headers={"Authorization": f"Bearer {API_KEY}"})
    return response.json()

# Get session details
session_data = get_session(session_id)
print(f"Messages: {session_data['messages']}")
```

### Error Handling

```python
import requests

def neuropetitorius_request(method: str, url: str, **kwargs):
    """Make a request with proper error handling"""
    try:
        response = requests.request(method, url, **kwargs)
        
        if response.status_code == 401:
            raise Exception("Authentication failed. Check your API key.")
        elif response.status_code == 429:
            raise Exception("Rate limit exceeded. Please try again later.")
        elif response.status_code >= 400:
            error_data = response.json()
            raise Exception(f"API Error: {error_data['error']['message']}")
        
        return response.json()
    
    except requests.exceptions.ConnectionError:
        raise Exception("Connection failed. Check the API URL.")
    except requests.exceptions.Timeout:
        raise Exception("Request timed out.")

# Usage
try:
    result = neuropetitorius_request(
        "POST",
        f"{BASE_URL}/v1/sessions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"topic_id": "test", "student_external_id": "test", "title": "test"}
    )
except Exception as e:
    print(f"Error: {e}")
```

### Streaming Responses

For a better user experience with longer AI responses, use Server-Sent Events (SSE):

```python
# See "Python Example (Streaming with SSE)" above
```

---

## Best Practices

1. **Secure Your API Key** - Never expose your API key in client-side code
2. **Handle Errors Gracefully** - Implement retry logic for transient errors
3. **Use Streaming for Long Responses** - Enable SSE for better UX
4. **Validate Input** - Check request parameters before sending
5. **Monitor Rate Limits** - Implement request throttling in your application

---

## Support

- **Email:** api-support@neuropetitorius.com
- **Documentation:** https://docs.neuropetitorius.com
- **Status Page:** https://status.neuropetitorius.com
