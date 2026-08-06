---
type: system
id: prompt-grammar
title: "Prompt-Grammar"
---

# Prompt Grammar

Every prompt the compiler emits has the same nine slots in the same order.
This page explains the order, because the order is doing work.

## The slots

| # | Slot | Source | Written by |
|---|---|---|---|
| 1 | FORMAT | duration + network `look.aspect`, `look.fps` | inherited |
| 2 | STYLE | channel `look` (film, lens, lighting, palette, grade, texture) | inherited |
| 3 | CAST | each character's `lock` | inherited |
| 4 | SETTING | location `lock` + prop `lock`s | inherited |
| 5 | ACTION | the shot's `action` | **the writer** |
| 6 | CAMERA | the shot's `camera`, else the channel default | **the writer** |
| 7 | DIALOGUE | the shot's `dialogue` | **the writer** |
| 8 | AUDIO | the shot's `audio` + the channel's bed | writer + inherited |
| 9 | CONTINUITY | previous clip's `last_frame`, this clip's `last_frame` | **the writer** |

Then a merged AVOID line: network negatives, channel negatives, then every
entity in the shot, then the shot's own.

## Why this order

**Format and style first.** Attention thins across a long prompt, and the
things that must never drift are the things that establish the world. Putting
the grade at the end is how you get a clip that's beautifully written and looks
like a different show.

**Locks before action.** The model should know who it is rendering before it is
told what they do. Identity stated after behaviour tends to get bent to fit the
behaviour.

**Action in the middle.** It is the only slot that changes between clips, and
the middle is where the room can afford variance.

**Continuity last.** It is an instruction about the clip's boundaries rather
than its content, and it reads most clearly after the content exists.

## Prose, not keywords

The compiler emits sentences, not comma-separated tags. Keyword soup was a
diffusion-era habit; video models are trained on caption-like prose and respond
to it better. Every field a writer fills should be a clause that could survive
being read aloud.

`--labeled` emits the same content with `[SLOT]` tags, for models or operators
that prefer explicit structure. The content is identical either way.

## What the writer must not do

- **Never restate a lock.** Not even a shortened version. "Vic, tired" in an
  `action` field competes with the lock and the model splits the difference.
- **Never describe the look.** Grade, stock, and colour are inherited. A writer
  asking for "warm light" fights [[Visual-System]] and usually wins, which is
  the problem.
- **Never write two events.** Ten seconds holds one. Two events is two clips,
  and the format is built to give you the second one.
