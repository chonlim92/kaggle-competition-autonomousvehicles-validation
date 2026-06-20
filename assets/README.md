# Assets Directory

This directory holds **localised text knowledge assets** grounding the AV Validation Orchestrator.

## Structure

```
assets/
└── knowledge/
    └── av_domain_glossary.md   # AV terminology and validation rules
```

## Usage

Assets are loaded at agent startup and injected into the system prompt or
retrieved via RAG when the agent answers domain-specific questions.

To add new knowledge:
1. Create a Markdown or plain-text file under `assets/knowledge/`.
2. Reference it from `src/agent/prompts.py` or register it as a knowledge source.
