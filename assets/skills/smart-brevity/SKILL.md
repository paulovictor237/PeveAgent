---
name: smart-brevity
description: "Rewrites and summarizes messages using Smart Brevity principles. Trigger this skill whenever the user asks to: summarize, shorten, reduce, simplify, rewrite, improve text, make more direct, cut text, make shorter, make a summary, synthesize, condense, or use 'smart brevity'. Also triggers on: 'summarize this', 'shorten this', 'make a summary', 'make it leaner', 'rewrite shorter', 'simplify this text', 'cut what is not needed', 'make more direct', 'smart brevity', 'brevity', or any request to shorten, summarize, improve, or rewrite a message or text. Use this skill even if the user just pastes a long text and says 'summarize' or 'shorten'."
disable-model-invocation: true
---

# Smart Brevity

Rewrites messages applying the principles from the book "Smart Brevity" by Jim VandeHei, Mike Allen, and Roy Schwartz.

IMPORTANT: All output MUST be in Brazilian Portuguese (pt-BR).

## Principles

1. **Lead with what matters** — First sentence must contain the most important information. If the reader only read one line, they'd get the point.
2. **Why it matters** — Right after the lead, one sentence on why the reader should care.
3. **Be direct** — Eliminate unnecessary words, jargon, redundancies, and filler. Every word must earn its place.
4. **Use visual structure** — Bullets, bold, and line breaks for easy scanning. Nobody reads walls of text.
5. **One thought per paragraph** — Never mix ideas. Each block communicates one thing.
6. **Cut in half, then cut again** — If the original has 200 words, the result should have ~50.

## Steps

### 1. Analyze the original message

Identify:

- The core message (what actually matters)
- The likely audience (colleague, manager, client, group)
- The appropriate tone (formal, casual, urgent)
- What is redundant, vague, or unnecessary

### 2. Rewrite applying Smart Brevity

Output format (always in pt-BR):

**[Title/Subject in 1 line — optional, for emails or announcements]**

[Lead: 1 sentence with the main information]

**Por que importa:** [1 sentence of context]

[Essential details in short bullets, if needed]

[Clear call to action, if any]

### 3. Present the result

Respond in the following format (Telegram-compatible, always in pt-BR):

```
✂️ Brevidade Inteligente

{rewritten message, using bold and bullets as appropriate}

📊 {N} → {M} palavras ({P}% menor)
```

Rules:

- The rewritten message must be ready to copy and resend
- Use **bold** to highlight the main point
- Use bullets (•) for lists, if applicable
- Keep line breaks for readability
- If the original message is already concise, return it as-is and replace the 📊 line with "✅ Mensagem já está concisa"
