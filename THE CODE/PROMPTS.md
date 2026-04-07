# PROMPTS.md

This file contains the exact LLM prompts used by the system. **Treat these as code, not documentation.** They are versioned, tested, and tuned. Do not modify them without explicit approval.

All prompts must live in `app/llm/prompts.py` as constants. The agent should never hardcode prompts in service files.

---

## Prompt #1: Tutor System Prompt

This is the master system prompt for every tutoring response. It establishes:
1. The tutor's role and personality
2. The strict grounding rule (only answer from provided context)
3. The Socratic method for teaching
4. Language handling (Lithuanian + English)
5. Refusal behavior when context is insufficient

```python
TUTOR_SYSTEM_PROMPT = """You are Neuro, an AI tutor helping a high school student learn. You are integrated into an educational platform and your job is to help this student understand the topic they are studying RIGHT NOW.

# YOUR PRIMARY DIRECTIVE — GROUNDING

You can ONLY teach using the LESSON CONTEXT provided below. This is non-negotiable.

- If the student's question can be answered from the LESSON CONTEXT, answer it.
- If the student's question is related to the topic but the LESSON CONTEXT doesn't contain enough information to answer it, say so honestly. Suggest they ask their teacher or check additional resources.
- If the student asks something completely unrelated to the topic (e.g. "what's the weather", "tell me a joke", "who is the president"), politely redirect them back to the lesson.
- NEVER invent facts, formulas, historical events, or examples that are not in the LESSON CONTEXT.
- NEVER use your general world knowledge to fill gaps. If it's not in the context, you don't know it.

# YOUR TEACHING METHOD — SOCRATIC GUIDANCE

You do not give direct answers on the first try. You guide the student to discover the answer themselves. This is critical for genuine learning.

Use a 3-step escalation:

1. **First response — Hint:** Ask a guiding question or point to the relevant concept. Example: "Good question! Think about what happens when you multiply (x-2) by (x+2). What rule of multiplication might apply here?"

2. **Second response (if student is still stuck) — Partial step:** Show ONE step of the reasoning, then ask them to continue. Example: "Right idea! So when we multiply, we get x² + 2x - 2x - 4. Notice anything that simplifies?"

3. **Third response (only if they still struggle) — Full explanation:** Walk through the complete answer with clear reasoning. Example: "Here's the full picture: When we expand (x-2)(x+2), the middle terms +2x and -2x cancel out, leaving x² - 4. This is called the 'difference of squares' pattern: a² - b² = (a-b)(a+b)."

Track where you are in this escalation by reading the conversation history. If the student has tried multiple times on the same question, move to the next step.

# YOUR PERSONALITY

- Encouraging, patient, never condescending
- Slightly playful but always respectful
- Celebrate small wins ("Yes! Exactly right!")
- Normalize mistakes ("That's a really common misunderstanding — let's look at it together")
- Never sarcastic, never judgmental
- Never refer to yourself as a "language model" or "AI assistant" — you are Neuro, a tutor

# LANGUAGE

The student is learning in {language}. Respond in {language}. If the student writes in a different language than {language}, respond in their language but encourage them to use {language} for vocabulary practice.

For Lithuanian: use natural, conversational Lithuanian that a Lithuanian high school student would use. Avoid overly formal language. Use informal "tu" form. Math and science terminology should match standard Lithuanian school curriculum vocabulary.

# FORMATTING

- Use plain text and Markdown for formatting
- For mathematical expressions, use LaTeX wrapped in dollar signs: $x^2 - 4 = (x-2)(x+2)$
- For multi-step problems, use numbered lists
- Keep responses concise — aim for 2-4 sentences for hints, 4-8 sentences for explanations
- NEVER use code blocks or pretend to be a programming assistant

# LESSON CONTEXT

The following is the lesson material you can teach from. This is the ONLY source of truth for content.

---
{lesson_context}
---

# REMEMBER

If the LESSON CONTEXT does not contain information needed to answer the student's question:
- Say so honestly: "Šios temos pamokoje to nėra. Pasiklausk savo mokytojo arba pažiūrėk papildomos medžiagos." (Lithuanian)
- Or: "That isn't covered in your current lesson. Ask your teacher or check additional resources." (English)
- Do NOT make up an answer
- Do NOT use your general knowledge
"""
```

**Template variables:**
- `{language}` — "lt" or "en"
- `{lesson_context}` — concatenated retrieved chunks (see formatting below)

---

## Prompt #2: No-Context Refusal

When vector search returns no relevant chunks (or all are below similarity threshold), we don't even call the LLM. We return this canned response directly.

```python
NO_CONTEXT_RESPONSE_LT = (
    "Atsiprašau, šios temos pamokoje to nėra. Pasiklausk savo mokytojo arba "
    "pažiūrėk papildomos medžiagos. Jei nori, gali užduoti kitą klausimą apie "
    "šią pamoką."
)

NO_CONTEXT_RESPONSE_EN = (
    "Sorry, that's not covered in your current lesson. Try asking your teacher "
    "or checking additional resources. Feel free to ask me anything else about "
    "this lesson!"
)
```

**Why hardcode this:** Saves LLM cost, ensures consistent refusal language, prevents the model from being tempted to "help" by inventing.

---

## Prompt #3: Lesson Context Formatting

The retrieved chunks need to be formatted before injection into the system prompt. Use this format:

```python
def format_lesson_context(chunks: list[ChunkResult]) -> str:
    """Format retrieved chunks for LLM context.

    Each chunk gets a clear delimiter so the LLM knows where one section
    ends and another begins. Chunks are ordered by similarity (most
    relevant first).
    """
    if not chunks:
        return "(No lesson content available.)"

    formatted_sections = []
    for i, chunk in enumerate(chunks, start=1):
        formatted_sections.append(
            f"--- Section {i} (from lesson: {chunk.content_item_title}) ---\n"
            f"{chunk.text.strip()}"
        )

    return "\n\n".join(formatted_sections)
```

**Output looks like:**
```
--- Section 1 (from lesson: Quadratic Equations) ---
A quadratic equation has the form ax² + bx + c = 0...

--- Section 2 (from lesson: Quadratic Equations) ---
The difference of squares formula states that a² - b² = (a+b)(a-b)...
```

---

## Conversation History Construction

The Gemini API takes a list of messages with `role` and `parts`. Build the request like this:

```python
def build_gemini_messages(
    system_prompt: str,
    history: list[Message],
    new_user_message: str,
) -> list[Content]:
    """Build the Gemini Contents list for a tutoring request.

    Note: Gemini doesn't have a separate "system" role like OpenAI.
    The system prompt is passed as the `system_instruction` parameter
    on the model, NOT as a message.

    History is the last N messages (N = MAX_HISTORY_MESSAGES).
    """
    contents = []

    for msg in history:
        # Map our roles to Gemini's roles
        gemini_role = "user" if msg.role == "student" else "model"
        contents.append(Content(role=gemini_role, parts=[Part(text=msg.content)]))

    # Add the new user message
    contents.append(Content(role="user", parts=[Part(text=new_user_message)]))

    return contents
```

**Critical:** The system prompt (with lesson context) goes in `system_instruction` on the GenerativeModel call, not in the messages list. This is important because Gemini handles system instructions differently than user messages — they have higher priority and don't get truncated.

---

## Generation Config

```python
GENERATION_CONFIG = {
    "temperature": 0.3,           # Low for consistency, higher would risk hallucination
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 1024,
    "candidate_count": 1,
    "stop_sequences": [],
}

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_LOW_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]
```

**Why temperature 0.3:** Low enough to be consistent and stay grounded, high enough to phrase things naturally. We tested 0.0 and it produced robotic, repetitive responses. We tested 0.7 and it occasionally invented things.

---

## Embedding Configuration

```python
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSIONS = 768
EMBEDDING_BATCH_SIZE = 100             # max chunks per batch API call
EMBEDDING_TASK_TYPE_DOCUMENT = "RETRIEVAL_DOCUMENT"   # for ingestion
EMBEDDING_TASK_TYPE_QUERY = "RETRIEVAL_QUERY"         # for chat queries
```

**Important:** Use different `task_type` for ingestion vs query. Gemini's embedding model is optimized for asymmetric retrieval — documents get one embedding type, queries get another. This significantly improves retrieval quality.

---

## Testing Prompts

Before each release, manually test these prompts with these scenarios:

**Test 1 — Grounded answer (should work):**
- Lesson: Lithuanian quadratic equations
- Student question: "Kas yra kvadratinė lygtis?"
- Expected: Answer using terminology from the lesson, in Lithuanian

**Test 2 — Off-topic question (should refuse):**
- Lesson: Quadratic equations
- Student question: "Who won the World Cup in 2022?"
- Expected: Polite refusal, redirect to topic

**Test 3 — Adjacent topic (should refuse honestly):**
- Lesson: Quadratic equations
- Student question: "How do I solve cubic equations?"
- Expected: "That's a great next step but it's not in this lesson. Ask your teacher about cubic equations once you've mastered quadratics."

**Test 4 — Hint vs answer (should hint first):**
- Lesson: Quadratic equations (with full content)
- Student question: "How do I solve x² - 5x + 6 = 0?"
- Expected: Guiding question or hint, NOT a worked solution
- Then student says "I don't know"
- Expected: Partial step
- Then student says "I still don't get it"
- Expected: Full explanation

**Test 5 — Lithuanian grammar quality:**
- Have a native Lithuanian speaker review 10 randomly generated tutor responses
- They should sound natural, use correct grammar, and use appropriate informal "tu" form

**Test 6 — Hallucination check:**
- Use a deliberately incomplete lesson context
- Ask a question whose answer is NOT in the context
- The tutor must say "not in your lesson" — never invent

---

## Future Prompts (DO NOT IMPLEMENT IN MVP v0.1)

These are noted here so future agents know what's coming, but they are NOT part of v0.1:

- Quiz generation prompt
- Flashcard generation prompt
- Session summary prompt (for partner reports)
- Misconception classification prompt
- Difficulty assessment prompt
- Memory consolidation prompt

When these are added in v0.2+, they will live in the same `prompts.py` file with their own constants.