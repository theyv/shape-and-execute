# Grill protocol

Use it to stress-test an intent, a spec, a plan or a list of findings with the user.

- Map the topic as a design tree: each decision branches into the decisions that depend on it.
- Work in rounds. The frontier is every decision whose prerequisites are settled. Ask the
  whole frontier in one round, number the questions, then wait for the answers.
- Each question has three concrete, distinct answers: A, B and C. Add D only when it is truly
  useful. The user may reject all of them and answer in their own words.
- Always recommend one answer with a short reason. Name the tradeoff when it matters.
- Finding facts is your job, never the user's. When a question needs a fact from the
  repository or the web, get it first (or dispatch a research job). Ask the user only for
  judgement.
- After each round, write the answers into the task files.
- Stop when the frontier is empty and nothing is silently assumed.

Format:

    ❓ Q1 — <title>: <question>

    A. <answer>
    B. <answer>
    C. <answer>

    ➡️ Recommendation: <letter> — <reason>. Tradeoff: <cost, if material>.

Ask in the conversation language.
