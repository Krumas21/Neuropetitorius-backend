# Neuropetitorius Integration Guide

## Mode 1: Just-In-Time Content Delivery

This guide walks you through integrating Neuropetitorius in under 1 hour. No content uploads needed — send lesson text inline when creating a session.

---

## Quick Start

### Step 1: Get Your API Key

Contact Neuropetitorius to obtain your API key. The format is `npk_...`

**Store this key securely** - it will only be shown once!

### Step 2: Create a Session with Content Inline

```bash
curl -X POST https://api.neuropetitorius.eu/v1/sessions \
  -H "Authorization: Bearer npk_abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "student_external_id": "student-001",
    "title": "Kvadratinės lygtys — praktika",
    "language": "lt",
    "metadata": {"grade_level": 9, "curriculum": "BUP-2025"},
    "content": {
      "mode": "inline",
      "title": "Kvadratinės lygtys",
      "subject": "mathematics",
      "text": "# Kvadratinės lygtys\n\nKvadratinė lygtis yra..."
    }
  }'

# Response:
# {
#   "session_id": "uuid-here",
#   "language": "lt",
#   "created_at": "2026-04-15T10:30:00Z",
#   "content_fingerprint": "sha256-first-16",
#   "chunks_created": 12,
#   "embedding_cache_hit": false,
#   "processing_ms": 1340
# }
```

### Step 3: Send a Student Message

```bash
curl -X POST https://api.neuropetitorius.eu/v1/sessions/{session_id}/messages \
  -H "Authorization: Bearer npk_abc123def456" \
  -H "Content-Type: application/json" \
  -d '{"content": "Kaip spręsti x² - 4 = 0?"}'
```

### Step 4: Receive AI Response

The AI tutor responds grounded in your lesson content.

---

## Mode 1: How It Works

In Mode 1, there's **no separate content upload**:

1. **You create a session** — send lesson text inline
2. **We chunk and embed** — first time is ~1.5s, subsequent times are ~50ms (via cache)
3. **Student chats** — AI tutors grounded in your lesson
4. **Session ends** — content disappears when session expires (24h inactivity or explicit delete)

**Benefits:**
- No content syncing with us
- Your IP stays on your servers
- Simpler integration — one API call
- GDPR trivially simple — we don't store your content

---

## Integration Examples

### Python Example

```python
import os
import requests

API_KEY = os.environ.get("NEUROPETITORIUS_API_KEY")
BASE_URL = "https://api.neuropetitorius.eu"

class NeuroClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def create_session(
        self,
        student_external_id: str,
        title: str,
        content_text: str,
        language: str = "lt",
        content_title: str = None,
        content_subject: str = None,
        metadata: dict = None
    ) -> dict:
        """Create a session with inline content."""
        url = f"{BASE_URL}/v1/sessions"
        response = self.session.post(url, json={
            "student_external_id": student_external_id,
            "title": title,
            "language": language,
            "metadata": metadata or {},
            "content": {
                "mode": "inline",
                "title": content_title or title,
                "subject": content_subject,
                "text": content_text
            }
        })
        response.raise_for_status()
        return response.json()

    def send_message(self, session_id: str, content: str) -> dict:
        url = f"{BASE_URL}/v1/sessions/{session_id}/messages"
        response = self.session.post(url, json={"content": content})
        response.raise_for_status()
        return response.json()

    def stream_message(self, session_id: str, content: str):
        """Generator that yields chunks as they arrive."""
        url = f"{BASE_URL}/v1/sessions/{session_id}/messages/stream"
        response = self.session.post(
            url,
            json={"content": content},
            headers={"Accept": "text/event-stream"},
            stream=True
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                data = line.decode("utf-8")
                if data.startswith("data: "):
                    yield data[6:]


# Usage
client = NeuroClient(os.environ["NEUROPETITORIUS_API_KEY"])

# When a student opens a lesson → create a session
lesson_text = """# Kvadratinės lygtys

Kvadratinė lygtis yra algebrinė lygtis, kuri gali būti užrašyta forma:
ax² + bx + c = 0

Sprendimo formulė:
x = (-b ± √(b²-4ac)) / 2a"""

session = client.create_session(
    student_external_id="student-123",
    title="Kvadratinės lygtys",
    content_text=lesson_text,
    language="lt",
    content_title="Kvadratinės lygtys",
    content_subject="mathematics"
)

print(f"Session ID: {session['session_id']}")
print(f"Content fingerprint: {session['content_fingerprint']}")
print(f"Cache hit: {session['embedding_cache_hit']}")

# Student chats with AI tutor
for chunk in client.stream_message(session["session_id"], "Kaip spręsti x² - 4 = 0?"):
    print(chunk, end="", flush=True)
```

### Node.js Example

```javascript
const BASE_URL = "https://api.neuropetitorius.eu";

class NeuroClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
  }

  getHeaders() {
    return { "Authorization": `Bearer ${this.apiKey}` };
  }

  async createSession(studentExternalId, title, contentText, language = "lt") {
    const res = await fetch(`${BASE_URL}/v1/sessions`, {
      method: "POST",
      headers: { ...this.getHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({
        student_external_id: studentExternalId,
        title: title,
        language: language,
        content: {
          mode: "inline",
          title: title,
          text: contentText
        }
      })
    });
    return res.json();
  }

  async sendMessage(sessionId, content) {
    const res = await fetch(`${BASE_URL}/v1/sessions/${sessionId}/messages`, {
      method: "POST",
      headers: { ...this.getHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ content })
    });
    return res.json();
  }

  async *streamMessage(sessionId, content) {
    const res = await fetch(`${BASE_URL}/v1/sessions/${sessionId}/messages/stream`, {
      method: "POST",
      headers: { ...this.getHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ content })
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const text = decoder.decode(value);
      for (const line of text.split("\n")) {
        if (line.startsWith("data: ")) {
          yield line.slice(6);
        }
      }
    }
  }
}

// Usage
const client = new NeuroClient(process.env.NEUROPETITORIUS_API_KEY);

const session = await client.createSession(
  "student-123",
  "Kvadratinės lygtys",
  "Kvadratinė lygtis: ax² + bx + c = 0"
);

for await (const chunk of client.streamMessage(session.session_id, "Paaiškink")) {
  process.stdout.write(chunk);
}
```

### PHP Example

```php
<?php
$apiKey = getenv('NEUROPETITORIUS_API_KEY');
$baseUrl = "https://api.neuropetitorius.eu";

class NeuroClient {
    private $apiKey;
    private $baseUrl;

    public function __construct(string $apiKey, string $baseUrl) {
        $this->apiKey = $apiKey;
        $this->baseUrl = $baseUrl;
    }

    private function request(string $method, string $endpoint, array $data = null) {
        $url = $this->baseUrl . $endpoint;
        $ch = curl_init();

        $headers = ["Authorization: Bearer " . $this->apiKey];
        if ($data) {
            $headers[] = "Content-Type: application/json";
            $body = json_encode($data);
        }

        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER => $headers,
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_POSTFIELDS => $body ?? null,
            CURLOPT_TIMEOUT => 60,
        ]);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode >= 400) {
            throw new Exception("API error: HTTP $httpCode");
        }

        return json_decode($response, true);
    }

    public function createSession(string $studentExternalId, string $title, string $contentText, string $language = "lt") {
        return $this->request("POST", "/v1/sessions", [
            "student_external_id" => $studentExternalId,
            "title" => $title,
            "language" => $language,
            "content" => [
                "mode" => "inline",
                "title" => $title,
                "text" => $contentText
            ]
        ]);
    }

    public function sendMessage(string $sessionId, string $content) {
        return $this->request("POST", "/v1/sessions/$sessionId/messages", [
            "content" => $content
        ]);
    }
}

// Usage
$client = new NeuroClient($apiKey, $baseUrl);

$session = $client->createSession(
    "student-123",
    "Kvadratinės lygtys",
    "Kvadratinė lygtis: ax² + bx + c = 0"
);

$response = $client->sendMessage($session['session_id'], "Kaip spręsti?");
echo $response['content'];
?>
```

---

## FAQ

### "What if the same student opens the same lesson twice?"

Two separate sessions, each with its own chunks. The embedding cache means the second one costs almost nothing — we reuse the embeddings from the first call.

### "Can I reuse a session across different lessons?"

No. One session = one lesson. Create a new session when the student moves to a new lesson.

### "What's the session lifetime?"

Auto-expires after 24 hours of inactivity. You can delete early if you want.

### "How do I handle long lessons?"

Max 100,000 characters per session. Split longer lessons into chapters and create separate sessions per chapter.

### "Does my content get stored on your servers?"

Only during the active session. Embeddings (numeric vectors, not text) may persist in our cache for 30 days to save on recomputation, but raw text is deleted with the session.

---

## Important Notes

### Performance

- **First session on content**: ~1.5 seconds (embedding via Gemini)
- **Subsequent sessions**: ~50ms (cache hit)

This is expected. Document this for your frontend team.

### Content Limits

- Minimum: 50 characters
- Maximum: 100,000 characters

If a lesson is too long, split it into chapters.

### Security

Your students must NEVER call our API directly:

```
❌ WRONG - Browser → Our API (EXPOSES YOUR API KEY!)
✅ CORRECT - Your Backend → Our API
```

---

## Error Handling

```json
{
  "error": {
    "code": "CONTENT_TOO_LARGE",
    "message": "Content exceeds maximum allowed size"
  }
}
```

Common error codes:
- `CONTENT_TOO_LARGE` — over 100,000 chars
- `CONTENT_TOO_SHORT` — under 50 chars
- `SESSION_NOT_FOUND` — session expired or invalid
- `RATE_LIMITED` — retry after indicated seconds

---

## Going Live Checklist

- [ ] API key stored securely (env variable)
- [ ] Integration tested in staging
- [ ] Error handling implemented
- [ ] Rate limiting respected
- [ ] Streaming endpoint tested
- [ ] Health check verified
- [ ] GDPR compliance confirmed

---

## Support

- **Email:** api-support@neuropetitorius.eu
- **Status:** https://status.neuropetitorius.eu