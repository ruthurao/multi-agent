import os

for _name in ("OLLAMA_MODEL", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
    os.environ.pop(_name, None)


def pytest_sessionfinish(session, exitstatus):
    if exitstatus == 5:
        session.exitstatus = 0
