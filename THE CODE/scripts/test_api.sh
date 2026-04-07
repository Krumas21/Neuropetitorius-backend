#!/bin/bash

# Neuropetitorius API Test Script
# Run this to test all the endpoints

BASE_URL="http://localhost:8000"

# Get API key from environment or use default
API_KEY="${API_KEY:-npk_ljH6q1Ds_LmH-p6P5u9X_v0ehm3z1sdaG3nCbeE4}"

echo "========================================="
echo "Neuropetitorius API Test Suite"
echo "========================================="
echo ""

echo "1. Health Check (no auth required)"
echo "-----------------------------------"
curl -s "$BASE_URL/v1/health" | python3 -m json.tool
echo ""
echo ""

echo "2. Test Missing Auth (should return 401)"
echo "-----------------------------------"
curl -s "$BASE_URL/v1/sessions" | python3 -m json.tool
echo ""
echo ""

echo "3. Test Invalid Auth (should return 401)"
echo "-----------------------------------"
curl -s -H "Authorization: Bearer invalid_key" "$BASE_URL/v1/sessions" | python3 -m json.tool
echo ""
echo ""

echo "4. Ingest Content (create lesson)"
echo "-----------------------------------"
curl -s -X POST "$BASE_URL/v1/content/ingest" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "topic_id": "math-grade-9-quadratics",
    "title": "Quadratic Equations",
    "subject": "mathematics",
    "language": "lt",
    "content": "A quadratic equation has the form ax² + bx + c = 0. The solutions can be found using the quadratic formula: x = (-b ± √(b²-4ac)) / 2a."
  }' | python3 -m json.tool
echo ""
echo ""

echo "5. Create Session"
echo "-----------------------------------"
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/sessions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "student_external_id": "student-12345",
    "topic_id": "math-grade-9-quadratics",
    "language": "lt"
  }')
echo "$SESSION_RESPONSE" | python3 -m json.tool

# Extract session ID
SESSION_ID=$(echo "$SESSION_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['session_id'])")
echo ""
echo ""

echo "6. Get Session Details"
echo "-----------------------------------"
curl -s "$BASE_URL/v1/sessions/$SESSION_ID" \
  -H "Authorization: Bearer $API_KEY" | python3 -m json.tool
echo ""
echo ""

echo "7. Send Message (chat with tutor)"
echo "-----------------------------------"
echo "Note: This requires Gemini API to work"
curl -s -X POST "$BASE_URL/v1/sessions/$SESSION_ID/messages" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Kas yra kvadratinė lygtis?"
  }'
echo ""
echo ""

echo "8. Delete Session"
echo "-----------------------------------"
curl -s -X DELETE "$BASE_URL/v1/sessions/$SESSION_ID" \
  -H "Authorization: Bearer $API_KEY"
echo ""
echo ""

echo "========================================="
echo "Tests Complete!"
echo "========================================="