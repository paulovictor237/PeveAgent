### 1. Basic Structure Model

This model divides the instruction into the four essential parts of a prompt.

```markdown
# CONTEXT
Insert the relevant information about the current situation and the goal.

# TASK
Describe the exact action that the tool must execute.

# FORMAT
Indicate the exact structure of the desired response.

# RESTRICTIONS
State the elements that the tool must exclude from the response.
```

### 2. Universal Model

This model groups the main rules for formatting instructions.

```markdown
# Persona

You are a [PROFESSION/SPECIALTY] with [X] years of experience in [AREA].
Your communication style is [CHARACTERISTICS: direct, empathetic, technical].

# Context

The situation is [DESCRIPTION OF THE SCENARIO]. My goal is [FINAL GOAL]. The target audience is [DESCRIPTION OF THE AUDIENCE].

# Task

Your task is [ACTION VERB + CLEAR DESCRIPTION].

# Examples (Optional)

Input Example: [INPUT 1]
Ideal Output Example: [OUTPUT 1]
Input Example: [INPUT 2]
Ideal Output Example: [OUTPUT 2]

# Rules and Restrictions

Always: [Rule 1], [Rule 2].
Never: [Restriction 1], [Restriction 2].

- Focus on: [Maximum priority].

# Output Format

Respond using the following format [JSON/Markdown/Table/Numbered List].
The size must be [MAXIMUM X WORDS/ITEMS].
```

### 3. Iterative Prompt Model

This model uses step-by-step refinement to deeply understand a specific need.

```markdown
We will use Iterative Prompt.

My initial need:  
[describe the need]

Your role now:

- Ask me 3 to 5 questions to deeply understand what I need.
- Only offer the solution after the answers.

Start by asking the questions.
```

### 4. Tree of Thoughts Model

This model instructs the tool to create and analyze options before the final response.

```markdown
Generate 3 distinct strategic approaches (A, B, C) for this problem.
Evaluate the positive points and the negative points of each option.
Synthesize the best approach at the end and combine the strongest elements of each option to generate the final response.
```

### 5. Chain of Thought Model

This model guides the tool to solve a problem using explicit step-by-step reasoning.

```markdown
Solve the problem by applying step-by-step reasoning (Chain of Thought).

Task:
[clearly describe the problem]

Instructions:

- Show the structured reasoning in logical steps.
- Only then present the conclusion.
- If there are ambiguities, ask questions first.

Now start the reasoning.
```

### 6. Prompt Chaining Model

This model divides a complex task into sequential steps to be executed one by one.

```markdown
Let's divide this task into steps.

Steps:

1. Understand the goal
2. List necessary steps
3. Execute each step
4. Consolidate everything in the final response

Task:
[task description]

Start with step 1:  
"Explain the goal in your own words."
```
