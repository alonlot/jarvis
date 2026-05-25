# Jarvis

> **Looking for the how-to?** → **[MANUAL.md](MANUAL.md)** has run / use /
> plugin tutorials with worked examples. This README is the design overview.

A personal AI assistant for Linux, designed around the Iron Man Jarvis pattern:
formal, voice-driven, and capable of actually doing work — not just answering
questions. It chats, listens, talks, watches a clock for scheduled routines,
and spawns autonomous `claude -p` agents when real changes are needed.

## What you get

- **Plugin tool system** — drop a Python file in `jarvis/tools/plugins/`,
  decorate functions with `@tool(...)`, restart. Auto-discovery picks them up
  and the assistant sees them in its prompt with name, description, and arg
  schema. Stubs included for mail, people search, calendar, and merge requests
  — replace them with your real APIs.
- **Routines** — cron-scheduled prompts that fire as if you'd typed them.
  `morning_briefing` and `end_of_day` are wired up by default; edit or add
  more in `~/.config/jarvis/config.yaml` or via the GUI.
- **Agent spawning** — when something needs real work (e.g. "fix the CR
  comments on my MR"), Jarvis asks first, then shells out to `claude -p` in
  the right repo to do it. Output streams back into the chat.
- **Voice in and out** — TTS and STT are each pluggable (local or remote).
  Either always-on wake-word ("hey jarvis") or push-to-talk hotkey.
- **PyQt6 GUI** — chat window, settings, routines manager, and a frameless
  always-on-top **arc-reactor overlay** that pulses while listening or
  talking. Drag to reposition; click to start listening.
- **Memory** — SQLite-backed long-term facts + rolling chat history. The
  assistant can `remember`, `recall`, and `forget` its own memories.
- **Two LLM backends** — `claude -p` (default; no API key, uses your Claude
  Code login) or any OpenAI-compatible endpoint (OpenAI, OpenRouter, Ollama,
  vLLM, LM Studio…). Pick independently for chat vs. agents.
- **Everything is also chat-controllable** — "set my TTS to remote with
  ElevenLabs", "add a routine that runs every Monday at 9am that…", "forget
  what you remembered about my standup time". The GUI is a convenience; the
  assistant can edit its own config.

## Install (Linux)

```bash
git clone <this repo> ~/jarvis
cd ~/jarvis
./install.sh
```

The script creates a venv, installs requirements, copies the default config
to `~/.config/jarvis/config.yaml`, and writes a (disabled) systemd user
service at `~/.config/systemd/user/jarvis.service`.

Suggested distro packages (Debian/Ubuntu):

```bash
sudo apt-get install -y portaudio19-dev libxcb-cursor0 python3-venv python3-dev
```

Optional, only if you want them:

```bash
pip install faster-whisper      # local STT
pip install openwakeword         # wake-word detection
```

## Run

```bash
.venv/bin/python jarvis.py              # GUI
.venv/bin/python jarvis.py --headless   # CLI chat
.venv/bin/python jarvis.py --say "good morning"
.venv/bin/python jarvis.py --run-routine morning_briefing
systemctl --user enable --now jarvis    # background service (optional)
```

## Configuration

Everything lives in `~/.config/jarvis/config.yaml`. The shipped default has
inline comments explaining every key. The Settings dialog (Jarvis → Settings…)
edits the same file.

### Choosing an LLM backend

```yaml
llm:
  backend: claude_cli     # uses `claude -p` — recommended
  # OR:
  backend: openai_compat
  openai_compat:
    base_url: "https://api.openai.com/v1"
    api_key_env: OPENAI_API_KEY
    model: "gpt-4o-mini"
```

The `agents:` section has the same shape but is independent — you can chat
with one backend and spawn work-agents with another (e.g. chat through a
cheap OpenAI-compat model, but do work with `claude -p`).

### TTS and STT

Both follow the same `enabled / backend (local|remote|none)` pattern. Remote
takes a `base_url`, model, and API key (literal or via env var).

The remote TTS payload matches OpenAI's `/v1/audio/speech` shape, which most
providers (ElevenLabs wrappers, self-hosted, etc.) emulate. Remote STT
matches `/v1/audio/transcriptions`.

### Wake word vs. push-to-talk

```yaml
voice_activation:
  mode: wake_word         # or push_to_talk, or off
  wake_word:
    model: "hey_jarvis"   # openWakeWord built-in
    silence_timeout_seconds: 10
  push_to_talk:
    hotkey: "ctrl+space"  # within the GUI
    silence_timeout_seconds: 10
```

`push_to_talk` mode listens after you click the overlay (or press the hotkey
while the chat window is focused). For a *truly* global hotkey across the
desktop, layer `pynput` on top — see the snippet in `voice/wake_word.py`.

## Writing a plugin

```python
# jarvis/tools/plugins/notion.py
from jarvis.tools.base import tool

@tool(
    name="search_notion",
    description="Search the user's Notion workspace.",
    args={
        "query": {"type": "string", "description": "What to look for."},
        "limit": {"type": "integer", "default": 10},
    },
)
def search_notion(assistant, *, query: str, limit: int = 10):
    # `assistant` exposes .config, .memory, .agents if you need them.
    token = assistant.config.resolve_secret("notion.api_key", "notion.api_key_env")
    ...
    return [{"title": "...", "url": "..."}]
```

That's it. Restart Jarvis; the model will see the tool with its description
and call it when relevant. The assistant calls tools via a simple text
protocol (`<tool_call>{...}</tool_call>`) so this works on any LLM backend.

## How agent spawning works

When the assistant decides a task needs real file edits (or you ask for it),
it calls the built-in `ask_user` tool with a question and an `action`
describing what would happen on "yes". The GUI surfaces the question. On
"yes" the runtime calls `AgentRunner.spawn`, which shells out to
`claude -p` (in the configured repo) with the proposed prompt. The agent's
final output streams back into the chat.

Default agent flags include `--permission-mode acceptEdits` so the agent
can actually edit files; tighten or loosen in `agents.claude_cli.extra_args`.

## Memory

Stored in `~/.local/share/jarvis/memory.db`. Two tables:

- `turns` — rolling chat history (`max_recent_turns` in config caps how much
  goes back into the prompt).
- `facts` — long-term key/value facts grouped by `kind`
  (`preference`, `identity`, `routine`, `note`, …).

Built-in tools: `remember`, `recall`, `forget`. The assistant uses them on
its own when something is worth keeping.

## Layout

```
jarvis.py                       entry point
config/default_config.yaml      shipped defaults
install.sh                      Linux installer (venv + systemd unit)
jarvis/
  core/
    config.py                   YAML config + dotted-path get/set + save
    memory.py                   SQLite turns + facts (FTS5)
    llm.py                      ClaudeCLI / OpenAI-compat backends
    agent_runner.py             claude -p subprocess jobs
    assistant.py                brain: tool loop, pending confirmations, hooks
  tools/
    base.py                     @tool decorator
    registry.py                 auto-discovery + built-ins
    plugins/
      git_tools.py              REAL: list repos, status, branches, activity
      merge_requests.py         REAL: GitHub + GitLab open MRs/PRs
      mail_stub.py              STUB — replace
      people_stub.py            STUB — replace
      calendar_stub.py          STUB — replace
  voice/
    tts.py                      local (pyttsx3) + remote (HTTP)
    stt.py                      local (faster-whisper) + remote (HTTP)
    wake_word.py                openWakeWord + VAD capture
  scheduler/
    routines.py                 APScheduler cron triggers
  gui/
    app.py                      QApplication wiring
    chat_window.py              chat + menu
    overlay.py                  arc-reactor overlay
    settings_dialog.py          tabs for every config section
    routines_dialog.py          CRUD for routines
```

## Roadmap / known gaps

- Stubs for mail, people search, and calendar — replace with your own APIs.
- `mr_review_comments` (per-MR CR notes) is a stub; wire it to your code
  review tool so the morning briefing can actually summarise CR notes.
- Global hotkey for push-to-talk currently only works while the GUI is
  focused. For a true desktop-wide hotkey, see the README note in
  `voice/wake_word.py`.
- Memory search is keyword (FTS5). For semantic recall, swap in a small
  embedding store (Chroma, sqlite-vec, etc.) behind `Memory.search_facts`.
