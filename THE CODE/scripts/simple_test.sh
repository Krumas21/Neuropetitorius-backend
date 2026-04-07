#!/bin/bash
# Simple test script with better error handling

API_KEY="npk_xy1rLr38P-UIqA1YCM1zxmr4vXM5K3-dZ5DSHcRU"

echo "=== 1. Health Check ==="
curl -s http://localhost:8000/v1/health
echo ""
echo ""

echo "=== 2. Ingest Content ==="
curl -s -X POST http://localhost:8000/v1/content/ingest \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"topic_id": "test-topic", "title": "Test", "language": "lt", "content": "Test content"}'
echo ""
echo ""

echo "=== 3. Create Session ==="
SESSION=$(curl -s -X POST http://localhost:8000/v1/sessions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"student_external_id": "student1", "topic_id": "test-topic", "language": "lt"}')
echo "$SESSION"
echo ""

# Extract session ID
SESSION_ID=$(echo "$SESSION" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
echo "Session ID: $SESSION_ID"
echo ""

echo "=== 4. Get Session ==="
curl -s http://localhost:8000/v1/sessions/$SESSION_ID \
  -H "Authorization: Bearer $API_KEY"
echo ""
echo ""

echo "=== 5. Send Message (Chat) ==="
curl -s -X POST http://localhost:8000/v1/sessions/$SESSION_ID/messages \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello tutor!"}'
echo ""
echo ""

echo "=== 6. Delete Session ==="
curl -s -X DELETE http://localhost:8000/v1/sessions/$SESSION_ID \
  -H "Authorization: Bearer $API_KEY"
echo "Deleted"
echo ""

echo "=== Done! ==="