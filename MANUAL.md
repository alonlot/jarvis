# Jarvis manual

A hands-on guide. The [README](README.md) covers the design; this is how you
actually run it, use it, and extend it.

---

## 1. Running it

### First launch

```bash
cd ~/jarvis            # wherever you cloned it
./install.sh           # creates .venv, installs deps, writes default config
.venv/bin/python jarvis.py
```

On first run Jarvis copies `config/default_config.yaml` to
`~/.config/jarvis/config.yaml`. Edit that file to set API keys, scan roots,
and routines. The chat window opens; the arc-reactor overlay appears in the
bottom-right corner of your screen.

### Daily use

Three ways to launch:

| Command | What it does |
|---|---|
| `python jarvis.py` | Full GUI: chat window + overlay + scheduled routines |
| `python jarvis.py --headless` | Terminal chat — useful over SSH |
| `python jarvis.py --say "..."` | One-shot: send a message, print reply, exit |
| `python jarvis.py --run-routine morning_briefing` | Fire a routine on demand |

To run as a background service so routines fire even when no terminal is
open:

```bash
systemctl --user enable --now jarvis     # uses the unit from install.sh
systemctl --user status jarvis           # see if it's running
journalctl --user -u jarvis -f           # tail the logs
```

### Logs

Logs go to stderr by default. With systemd they're in journalctl. Set the
verbosity in `config.yaml`:

```yaml
logging:
  level: DEBUG     # INFO | DEBUG | WARNING
```

Or per-launch: `python jarvis.py --log-level DEBUG`.

---

## 2. Using it

### Chat

Type into the input box and hit Enter. Replies appear in the transcript
above. Markdown isn't rendered — Jarvis is concise enough that it doesn't
matter.

Useful asks once you're set up:

- "What's on my schedule today?"
- "List my open merge requests"
- "Summarise what I committed last week across all my repos"
- "Remember that my standup is at 9:45 every weekday"
- "What did you remember about me?"
- "Add a routine called `lunch_check` that runs at 12:30 weekdays and asks
  whether I want it to summarise any new mail since 10am"

The assistant has a **tool loop**: when it needs information, it calls a
tool, reads the result, and either replies or calls another tool. You'll
sometimes see a short pause — that's a tool round-trip.

### Voice

Set the mode in **Settings → Voice activation**:

- **`push_to_talk`** (default): click the overlay or press the hotkey
  (`ctrl+space` by default, configurable). Speak until you stop; Jarvis
  detects 10s of silence and transcribes.
- **`wake_word`**: Jarvis listens constantly. Say "hey jarvis" (or whichever
  openWakeWord model you've picked) and it starts capturing. Same 10s-silence
  cutoff. Requires `pip install openwakeword`.
- **`off`**: text only.

The overlay reflects state:

| State | Look |
|---|---|
| idle | Quiet cyan ring |
| listening | Brighter cyan, pulsing |
| processing | Purple, spinning arc |
| talking | Warm orange, pulsing |

Drag the overlay to reposition. The position resets to your config on
restart — set `overlay.position` if you want a different default.

### Routines

A routine is a cron-scheduled prompt. When it fires, it goes through the
same machinery as if you'd typed it — tools, agent confirmation, memory,
everything.

Edit routines via **Jarvis → Routines…** in the menu, or talk to Jarvis:

> "Add a routine called `friday_review` that runs every Friday at 5pm and
> lists my unmerged branches with their last commit date."

Five-field cron, standard format:

```
min  hour  day-of-month  month  day-of-week
0    8     *             *      1-5      # 8am weekdays
*/15 *     *             *      *        # every 15 minutes
0    9     1             *      *        # 9am on the 1st of each month
```

"Run now" in the routines dialog fires a routine immediately — useful when
you've just added one and want to see what it does.

### Agents (the "and do it" part)

Whenever Jarvis is about to do something **side-effecting** — edit files,
post a comment, send mail — it should call its `ask_user` tool first. You
see a question in the chat; your next message is the answer.

Example flow:

```
You: morning_briefing
Jarvis: You have 3 open MRs. apps#123 has 2 unresolved CR comments asking
        you to extract the loader logic and add a test. Shall I spawn an
        agent to fix them, sir?
You: yes
Jarvis: Very good, sir. I've spawned agent agent-0001 to work on that in
        /home/alon/code/apps. I'll report back when it finishes.
        ... (a few minutes later) ...
Jarvis: Agent agent-0001 finished with status done. Last output: ...
```

Under the hood that's `claude -p` running in the repo with
`--permission-mode acceptEdits`. Tighten or loosen in
`config.yaml → agents.claude_cli.extra_args`.

### Memory

Two layers:

- **Chat history** — the last `memory.max_recent_turns` turns go into the
  prompt automatically. Clear it from Jarvis → Clear chat history.
- **Long-term facts** — typed key/value entries grouped by `kind`
  (`identity`, `preference`, `routine`, `project`, `note`, …). Stored in
  `~/.local/share/jarvis/memory.db` (SQLite, FTS5).

#### Pinned vs. indexed (the important part)

Dumping every fact into every prompt wastes tokens and gets worse as memory
grows. Jarvis uses a two-tier model:

- **Pinned facts** appear in every system prompt with their full value. This
  is reserved for things the assistant needs *every turn* — your name, how
  you like to be addressed, persistent preferences. Should be a handful.
- **Indexed facts** are listed by `kind: key1, key2, …` only. The values
  are not sent. The assistant fetches them on demand with
  `read_memory(kind, key)` when relevant.

What this means in practice:

```
# Memory
You have 47 long-term facts (4 pinned). ...

## Pinned (always available)
- [identity] name: Alon
- [preference] address_style: sir
- [preference] brevity: terse
- [identity] employer: MyCorp

## Index (fetch with `read_memory` when relevant)
identity: name, employer, manager, team
preference: address_style, brevity, voice_provider, mr_review_style
project: jarvis, dashboard, infra_migration
routine: standup, lunch_check, end_of_day
note: vacation_aug, neighbor_dog_name, ssh_alias_for_jumphost
```

The model sees that `note.neighbor_dog_name` exists; if you ask "what's my
neighbor's dog called?" it calls `read_memory(kind="note", key="neighbor_dog_name")`
and reads just that one fact.

#### What to pin

Pin when **either** is true:

- The fact's relevance is **constant** — every reply should reflect it
  (your name, address style, persona preferences).
- The fact is **so frequently needed** that the round-trip cost of fetching
  is worse than the prompt cost of including it (e.g. your timezone if
  most questions are time-sensitive).

For anything situational ("the IP of my dev VPN", "the slug of last
quarter's design doc"), leave it unpinned. The model finds it via the index.

#### Asking Jarvis to manage memory

```
You: remember that my standup is at 9:45 every weekday
Jarvis: Noted, sir. [calls remember(kind="routine", key="standup",
        value="9:45 every weekday")]

You: pin that I prefer terse responses
Jarvis: [calls remember(... pinned=true) or pin_memory(...)]

You: what do you remember about my projects?
Jarvis: [sees `project: jarvis, dashboard, infra_migration` in index,
        calls read_memory(kind="project") to fetch all values]

You: forget the dashboard project
Jarvis: [calls forget(kind="project", key="dashboard")]
```

#### Does this work with `claude -p`?

Yes. The memory injection happens at the **assistant** level, before any
LLM call. The system prompt with pinned + index is built from SQLite and
passed to whichever backend you've configured. `claude -p` sees the exact
same prompt as the OpenAI-compatible backend would — backend choice doesn't
change memory behaviour.

(One subtle thing: `claude -p` is stateless per invocation, but so is every
LLM API call. The illusion of memory is built by re-injecting the system
prompt and recent turns on every call. Jarvis handles that for you.)

#### Memory tools (built in)

| Tool | What it does |
|---|---|
| `remember(kind, key, value, pinned=false)` | Upsert a fact; preserves existing pinned state if not set |
| `pin_memory(kind, key, pinned=true)` | Pin or unpin an existing fact |
| `read_memory(kind?, key?)` | Exact fetch. Both args → one fact. `kind` only → all of that kind. Neither → the index |
| `recall(query, limit=8)` | Fuzzy FTS search across all facts |
| `forget(kind?, key?)` | Remove facts. No args = wipe all |

#### When the model should *not* dump memory on you

Built into the prompt: "DO NOT ask the user about something already in
memory." If you've told Jarvis your timezone once, it should never ask
again. If it does, that's a description / prompt bug — either the kind/key
naming is too obscure for the model to find it in the index, or the fact
was stored under a name the model wouldn't guess. Rename it (`forget` +
`remember` under a better key).

### Settings

**Jarvis → Settings…** has tabs for every config section. Save persists
back to `~/.config/jarvis/config.yaml`. Changing the chat LLM backend
rebuilds it immediately; changing voice settings takes effect on the next
mic open.

You never *need* the dialog — anything in it is also settable by talking
to Jarvis ("set my STT backend to remote", "use the openai_compat backend
with model gpt-4o-mini", etc.).

---

## 3. Adding plugins (giving Jarvis more capabilities)

### The pattern

A plugin is one Python file under `jarvis/tools/plugins/`. Each function
decorated with `@tool(...)` becomes available to the assistant.

```python
# jarvis/tools/plugins/notion.py
from jarvis.tools.base import tool

@tool(
    name="search_notion",
    description="Search the user's Notion workspace and return matching pages.",
    args={
        "query": {"type": "string", "description": "What to search for."},
        "limit": {"type": "integer", "default": 10},
    },
)
def search_notion(assistant, *, query: str, limit: int = 10):
    token = assistant.config.resolve_secret("notion.api_key", "notion.api_key_env")
    # ...call the API...
    return [{"title": "...", "url": "..."}]
```

Drop the file, restart Jarvis, ask: "Search Notion for the Q3 roadmap."
That's it.

### The contract

| Field | Purpose | Used by |
|---|---|---|
| `name` | How the assistant calls it | Tool dispatch |
| `description` | One sentence; what does this do? | System prompt — this is how the LLM decides when to use it |
| `args` | Arg schema (`type`, optional `default`, optional `description`) | System prompt + runtime kwarg filtering |
| Return value | Any JSON-serialisable thing — dict, list, string, number | Inlined back to the LLM as the tool result |

The first parameter `assistant` is optional. If present, you get the live
`Assistant` instance: `assistant.config`, `assistant.memory`,
`assistant.agents`. Use it for secrets, persistence, or to spawn sub-agents.

### Worked example: a real plugin

Suppose you have a Python module `mycorp_api.py` that wraps your internal
HR system. Wire it in like this:

```python
# jarvis/tools/plugins/hr.py
from jarvis.tools.base import tool
from mycorp_api import HRClient   # your existing module


def _client(assistant) -> HRClient:
    base = assistant.config.get("hr.base_url")
    token = assistant.config.resolve_secret("hr.api_key", "hr.api_key_env")
    return HRClient(base_url=base, token=token)


@tool(
    name="lookup_employee",
    description="Look up an employee by email or name. Returns title, team, manager, and timezone.",
    args={"who": {"type": "string", "description": "Email, full name, or partial name."}},
)
def lookup_employee(assistant, *, who: str):
    e = _client(assistant).find(who)
    if not e:
        return {"found": False, "query": who}
    return {
        "found": True,
        "name": e.name, "email": e.email, "title": e.title,
        "team": e.team, "manager": e.manager, "tz": e.timezone,
    }


@tool(
    name="report_pto",
    description=(
        "Request paid time off. Returns a request_id and pending_approver. "
        "Use sparingly — confirm with the user before calling."
    ),
    args={
        "start": {"type": "string", "description": "ISO date e.g. 2026-06-12"},
        "end": {"type": "string", "description": "ISO date e.g. 2026-06-19"},
        "reason": {"type": "string", "default": ""},
    },
)
def report_pto(assistant, *, start: str, end: str, reason: str = ""):
    res = _client(assistant).request_pto(start=start, end=end, reason=reason)
    return {"request_id": res.id, "pending_approver": res.approver}
```

Add the matching config keys to `~/.config/jarvis/config.yaml`:

```yaml
hr:
  base_url: "https://hr.mycorp.internal"
  api_key_env: MYCORP_HR_TOKEN
```

Restart Jarvis. Ask "who is jane@mycorp.com?" — Jarvis will call
`lookup_employee` and answer from the result.

### Designing tool descriptions

The description is the **only** thing the LLM uses to decide whether to call
your tool. A few rules that consistently work:

- **Lead with the verb-noun:** "Look up an employee by …", "Search the Notion
  workspace …", "Send an email via …". The model scans descriptions linearly.
- **Mention side effects explicitly.** If the tool writes anything (mail,
  PTO, files), say so. Jarvis is more cautious with tools whose descriptions
  contain words like "send", "create", "delete".
- **State limits and units.** "Returns up to N most-recent items, newest
  first." "Date arg is ISO yyyy-mm-dd."
- **For dangerous tools, hint at confirmation.** Add a clause like
  "Use sparingly — confirm with the user before calling." The model will
  reliably call `ask_user` first.

### Returning data the model can use

Return small, structured things. The result is stringified and inlined as a
tool message, so:

- **Lists of objects** > flat lists of strings. The model can summarise a
  list of `{title, url, due}` dicts; a list of `"foo, bar, baz"` strings
  loses structure.
- **Cap your output.** Tool results are truncated to ~8000 chars before
  going back to the model. If your API can return 10k rows, paginate and
  ask the model to call you again.
- **Errors as data, not exceptions.** If the tool can fail gracefully,
  return `{"error": "…"}` instead of raising. The assistant will see the
  error string and decide what to tell you.

### Using `ask_user` from inside a plugin

If your tool wants to ask the user something itself (not just before calling
it), don't implement that in the plugin — return a result and let the
assistant emit `ask_user` from the next LLM turn. The text protocol is
designed so the assistant stays in charge of the dialogue.

### Spawning a sub-agent from a plugin

For long-running work you don't want to block on:

```python
@tool(
    name="fix_lint_in_repo",
    description="Spawn an agent to fix lint issues in a repo. Returns the job id.",
    args={"repo": {"type": "string"}},
)
def fix_lint_in_repo(assistant, *, repo: str):
    prompt = f"Run the linter in {repo} and fix every reported issue. "\
             f"Commit on a branch named lint/auto-fix."
    job = assistant.agents.spawn(prompt, cwd=repo)
    return {"job_id": job.id, "status": job.status}
```

The agent runs in a background thread; its output and exit status come back
into the chat via the `on_agent_update` callback wired up in
`Assistant._on_agent_done`.

### Built-in tools you can lean on

These are always available (registered in `jarvis/tools/registry.py`):

| Tool | Purpose |
|---|---|
| `remember(kind, key, value)` | Store a long-term fact |
| `recall(query, limit)` | Search long-term memory |
| `forget(kind?, key?)` | Remove facts |
| `set_config(key, value)` | Write any config key (persists to disk) |
| `get_config(key)` | Read a config key |
| `add_routine(name, cron, prompt, ask_before_acting)` | Add / replace a routine |
| `remove_routine(name)` | Remove a routine |
| `list_routines()` | List routines |
| `spawn_agent(prompt, cwd?)` | Spawn a `claude -p` agent directly (no confirmation) |
| `list_tools()` | Enumerate available tools (handy for "what can you do?") |
| `ask_user(question, action?)` | Pause and ask the user; runtime stashes the action for the answer |

### Debugging a plugin

1. **Did it load?** Start with `--log-level DEBUG`. Look for
   `Loaded N tools: …` — your tool name should be in there. If a plugin
   raises at import, you'll see `Failed to load plugin …` instead.
2. **Does the model know about it?** Ask Jarvis "what tools do you have?"
   or call `list_tools`.
3. **Is it being called?** DEBUG logs include `Running …` for CLI backends
   and `POST …` for HTTP. The tool result is logged at info level.
4. **Bad JSON in the call?** The model occasionally hallucinates arg names.
   The runtime filters kwargs to your declared `args` schema, so an unknown
   arg becomes a silent omission. Make your descriptions explicit about
   required args.

### Conventions in this repo

- **One plugin file = one capability** (mail, HR, calendar, notion, …).
  Don't mix.
- **Real plugins drop the `_stub` suffix.** Replace `mail_stub.py` with
  `mail.py` once you implement it; delete the stub.
- **Secrets live in config or env vars**, never hardcoded. Use
  `assistant.config.resolve_secret(literal_key, env_var_key)`.
- **Stay synchronous.** Tools run on a worker thread; long calls are fine
  but don't spawn your own `asyncio` event loop inside a tool — it'll
  conflict with PyQt's. Use `assistant.agents.spawn` for truly async work.

---

## 4. Tips, pitfalls, and patterns

### Make routines push, not pull

A routine that just *says* "you have 3 MRs" is OK. A routine that *acts* —
"…and I've drafted a fix for #123, shall I commit?" — is the point of
having Jarvis. Build your morning briefing so it ends with a question and
a ready-to-spawn agent.

### Trust the wake word, but verify

Wake-word detection has false positives. For destructive tools the
assistant should always `ask_user` first, even in voice mode — that gives
you a chance to say "no" before anything happens.

### Local vs remote voice

| | Local | Remote |
|---|---|---|
| Latency | Lower (no network) | Higher |
| Quality | Modest (pyttsx3, base whisper) | Excellent (good models) |
| Privacy | Stays on-device | Goes to the provider |
| Cost | Free | Per request |

A common setup: **local STT** (fast, private, "good enough") + **remote TTS**
(better Jarvis-like voice). Mix and match per backend.

### When the model misuses a tool

Adjust the **description**, not the code. Descriptions are the model's only
view of the tool. Examples:

- Tool gets called too eagerly → add "Only call when the user explicitly
  asks about X."
- Tool gets called with wrong args → add `"description": "..."` lines on
  the args and re-list the expected format in the tool description.
- Tool gets ignored when it should fire → strengthen the verb and add the
  most likely user phrasings into the description ("…for questions like
  'who is …' or 'what does … do at the company'").

### Where things live

| Thing | Path |
|---|---|
| Code | `~/jarvis/` (wherever you cloned) |
| Config | `~/.config/jarvis/config.yaml` |
| Memory DB | `~/.local/share/jarvis/memory.db` |
| Logs (systemd) | `journalctl --user -u jarvis` |
| Agent working dirs | Wherever you configure / wherever the agent is spawned |

### What to do when something breaks

1. `python jarvis.py --headless --log-level DEBUG` — gives you logs in your
   terminal and a chat prompt to reproduce.
2. Comment out a suspect plugin file's contents and restart — narrows down
   which plugin is misbehaving.
3. Sanity-check the LLM directly with `--say "ping"` to isolate voice/GUI
   vs LLM-pipeline issues.
4. The agent output of a failed run is in `assistant.agents.jobs[id]`;
   ask Jarvis "show me the output of agent agent-0001."
