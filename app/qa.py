from app.llm import chat
from app.retrieval.search import search_code

SYSTEM_PROMPT = """You are a codebase analysis assistant.
Use only the retrieved repository snippets provided.
Always cite file paths and line ranges like (app/routes/users.py:18-44).
Do not claim a function, API, dependency, or test exists unless it appears in the snippets.
If the evidence is insufficient, say which file or information is missing."""


def format_context(hits):
    blocks = []
    for h in hits:
        header = f"### {h['file_path']}:{h['start_line']}-{h['end_line']} ({h['symbol']})"
        blocks.append(f"{header}\n```{h['language']}\n{h['content']}\n```")
    return "\n\n".join(blocks)


def answer(repo_id: str, question: str):
    hits = search_code(repo_id, question)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Snippets:\n{format_context(hits)}\n\nQuestion: {question}"},
    ]
    return chat(messages), hits