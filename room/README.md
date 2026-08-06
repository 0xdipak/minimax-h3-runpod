# The Writers' Room

An Obsidian vault and a compiler. Writers write beats; the compiler emits
prompt packages for the video pipeline.

**Open this folder — `room/` — as the Obsidian vault root.** It is deliberately
separate from the video engineering project at the repository root; the two
halves share a repo and nothing else. See [the handoff contract](00-System/Handoff-Contract.md).

## Quick start

```bash
cd room
python3 tools/roomctl.py ls        # the network at a glance
python3 tools/roomctl.py lint      # validate everything
python3 tools/roomctl.py build     # write _build/<channel>/<episode>/
```

Requires Python 3.10+ and PyYAML. Nothing else.

## The idea in one paragraph

Video models drift — ask twice for "a tired night clerk" and you get two
different men. So every recurring character, location, and prop owns one
canonical sentence, its **lock**, and that exact sentence is injected verbatim
into every prompt it appears in. Writers never retype a lock; they link to it,
and the compiler substitutes. What a writer actually writes is four fields per
clip: `action`, `camera`, `dialogue`, `last_frame`. Everything else — grade,
palette, faces, rooms, sound bed, prohibitions — arrives by inheritance down
the chain **Network → Channel → Series → Episode → Shot**.

## Layout

| Path | What it is |
|---|---|
| `00-System/` | How the machine works. Read once, in order. |
| `05-Network/` | The network note. Binds every channel; kept short on purpose. |
| `10-Channels/` | One self-contained folder per channel. |
| `90-Templates/` | Note templates, plus `_Channel/` — the channel scaffold. |
| `tools/roomctl.py` | The compiler. Writers never open it. |
| `_build/` | Generated. Never edited, never committed, safe to delete. |

## Start here

1. [How This Vault Works](00-System/How-This-Vault-Works.md)
2. [Prompt Grammar](00-System/Prompt-Grammar.md) — the nine slots, and why that order
3. [Shot Grammar](00-System/Shot-Grammar.md) — what fits in ten seconds
4. [Beat Structures](00-System/Beat-Structures.md) — shapes for a 3–5 clip post
5. [Handoff Contract](00-System/Handoff-Contract.md) — the seam with video engineering

Then read [Night Shift Supply](10-Channels/Night%20Shift%20Supply/Night%20Shift%20Supply.md)
and the worked episode, [A Single Egg](10-Channels/Night%20Shift%20Supply/Episodes/ep-001-a-single-egg.md),
which compiles to four clips with zero warnings.

## Adding a channel

```bash
python3 tools/roomctl.py new channel "Channel Name"
```

Scaffolds the folder, four doctrine notes, and empty canon. The scaffold's
`look` fields are marked `TODO`, and `lint` refuses to compile a channel that
still has them — placeholder prose that compiles is placeholder prose that
ships.
