<!-- L0: NotebookLM CLI — auth, создание блокнотов, YouTube анализ, Playwright fallback -->
# NotebookLM Integration

## Setup
- **CLI**: `notebooklm` (install via `pip install notebooklm-py`)
- **Auth**: `notebooklm login` (opens browser for Google OAuth)
- **Language**: `notebooklm language set ru`

## Best For
- YouTube video analysis (understands actual audio, not just auto-subtitles)
- Document summarization from multiple sources
- Podcast-style audio generation from documents
- Technical content where auto-subtitles mangle terms

## Workflow

```bash
# 1. Create a notebook
notebooklm create "My Research" --json
# Returns notebook_id

# 2. Add sources
notebooklm source add <notebook_id> --youtube "https://youtube.com/watch?v=..."
notebooklm source add <notebook_id> --file document.pdf
notebooklm source add <notebook_id> --url "https://example.com/article"

# 3. Wait for processing
notebooklm source wait <notebook_id>

# 4. Ask questions
notebooklm ask <notebook_id> "What are the key points?"

# 5. Generate audio overview
notebooklm generate <notebook_id>
```

## Tips
- Use `--json` flag when parsing output programmatically (for extracting IDs).
- YouTube advantage over yt-dlp: works with actual audio track, catches domain-specific terms correctly.
- Multiple sources in one notebook = cross-referencing between them.

## Gotchas
- **Rate limits**: audio/video generation may fail under load. Retry after 5-10 minutes.
- **Source processing**: large files take time. Always `source wait` before asking.
- **Audio generation**: not instant, can take 2-5 minutes.
- **Google account required**: same Google account as other GCP services.
