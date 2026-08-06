---
type: system
id: how-this-vault-works
title: "How-This-Vault-Works"
---

# How This Vault Works

Open this folder as an Obsidian vault. Everything else follows from one idea.

## The idea

Video models drift. Ask one for "a tired night clerk" twice and you get two
different men. The room cannot fix that with better prose, so it doesn't try —
it fixes it with **repetition**. Every recurring thing in the network owns one
canonical sentence, its **lock**, and that exact sentence is injected into every
prompt the thing appears in. Byte-identical, every time.

The consequence is the whole system: **a writer must never retype a lock.** If
a writer describes Vic in their own words, Vic changes. So writers link, and
the compiler substitutes.

## What a writer actually writes

Four fields per clip:

```yaml
action:  what physically happens
camera:  the framing and whether it moves
dialogue: who says what
last_frame: the image the next clip opens on
```

Everything else — the stock, the grade, the palette, the faces, the room, the
sound bed, the things that must never appear — arrives by inheritance.

## The chain

```
Network      the format, the legal floor, the handoff contract
  └ Channel  the look, the voice, the sound, the cast
      └ Series    a repeatable shape
          └ Episode    one post, 3–5 clips
              └ Shot       one 10-second clip
```

Each layer may **tighten** what it inherits. No layer may contradict one. If a
channel needs to break a network rule, the rule was never a network rule.

## The folders

| Folder | What lives there |
|---|---|
| `00-System/` | How the machine works. Read once. |
| `05-Network/` | [[Network]] — binds every channel. Kept deliberately short. |
| `10-Channels/` | One folder per channel, self-contained. |
| `90-Templates/` | Note templates, and the channel scaffold. |
| `tools/` | The compiler. Writers never open it. |
| `_build/` | Generated. Never edited, never committed, safe to delete. |

Inside a channel: the channel note, four doctrine notes, `Canon/`, `Series/`,
`Episodes/`. Channels do not reach into each other except for deliberate
crossovers.

## Working the graph

Turn on Obsidian's graph view. A healthy channel looks like a dense knot of
canon with episodes hanging off it. Two things to watch for:

- **An orphan** — a character no episode links to. Either write them in or
  cut them; canon that isn't used is canon nobody remembers.
- **A hub with one link** — a location used once. Locations get valuable
  through repetition, so a one-use room is usually a room that should have
  been an existing one.

## The commands

```bash
tools/roomctl.py ls                              # the network at a glance
tools/roomctl.py new channel "Channel Name"      # scaffold a channel
tools/roomctl.py new episode "Title"             # start a post
tools/roomctl.py lint                            # before you commit
tools/roomctl.py build                           # hand off to video
```

`lint` is the room's second reader. It catches a link that resolves to nothing,
a character with no lock, a clip with no `last_frame` for the next one to match,
a post that runs long, and a crossover nobody meant to write.

## The seam

The room stops at `_build/`. What happens to a prompt after that — which model,
which parameters, how many retries — belongs to the video engineering side, and
this vault deliberately knows nothing about it. See [[Handoff-Contract]].
