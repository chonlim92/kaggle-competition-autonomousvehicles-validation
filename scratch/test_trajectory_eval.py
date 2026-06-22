import asyncio
import json
from pathlib import Path
from src.agent.agent import root_agent
from src.skills.pii_redactor.scripts.enterprise_av_security_pii_cleaner import clean_pii

# We want to record which tools were called
called_tools = []

original_clean_pii = clean_pii

def mock_clean_pii(*args, **kwargs):
    called_tools.append("clean_pii")
    return original_clean_pii(*args, **kwargs)

async def test_run():
    # Patch the function in the FunctionTool
    for t in root_agent.tools:
        if getattr(t.func, '__name__', '') == 'clean_pii':
            t.func = mock_clean_pii

    runner = root_agent.get_runner()
    res = await runner.run_async("Please clean this PII: John Smith")
    print("Response:", res.text)
    print("Called Tools:", called_tools)

asyncio.run(test_run())
