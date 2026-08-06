---
type: system
id: handoff-contract
title: "Handoff-Contract"
---

# Handoff Contract

Where the writers' room ends and video engineering begins.

## The rule

**The room describes intent. The engineering side decides execution.**

The room never names a model, a parameter, a resolution, a seed, a sampler, a
retry policy, or a cost. It has no opinion on any of them. In exchange, the
engineering side never edits a prompt's meaning — if a prompt doesn't work, it
comes back to the room as a note, not as a rewrite.

This is what lets both halves change independently. The model underneath can be
swapped entirely and no note in this vault needs touching.

## What crosses

`tools/roomctl.py build` writes, per episode:

```
_build/<channel-id>/<episode-id>/
├── shot-01.txt          paste-ready prompt, one per clip
├── shot-02.txt
├── ...
├── manifest.json        the machine-readable handoff
└── CONTACT-SHEET.md     the human-readable review sheet
```

`_build/` is generated output. It is never edited by hand and never committed —
every file in it is reproducible from the notes.

## manifest.json

`handoff_schema: "writers-room/1"`. Additive changes only; a breaking change
gets a new version string and a conversation.

| Field | Meaning |
|---|---|
| `network`, `channel`, `channel_id` | Which account this post belongs to. |
| `series`, `episode`, `title` | Provenance, back to the source note. |
| `premise`, `hook` | Editorial context. Not for the model. |
| `aspect`, `fps` | Delivery format, inherited from the network. |
| `total_seconds` | Sum of clip durations. |
| `post` | Caption, hashtags, sound. For whoever publishes, not the model. |
| `shots[]` | The clips, in order. |
| `shots[].id` | Stable, `<episode-id>-<nn>`. Safe to use as a job key. |
| `shots[].duration_seconds` | What the clip should run. |
| `shots[].prompt` | The prompt as prose. The default. |
| `shots[].prompt_labeled` | The same content, `[SLOT]`-tagged. |
| `shots[].negative_prompt` | Comma-joined. Intent, not syntax. |
| `shots[].blocks` | The prompt split by slot, if a model wants fields. |
| `shots[].last_frame` | The image this clip ends on. |
| `shots[].cast`, `location`, `props` | Which canon entities appear. |

## Notes for the other side of the seam

- **`blocks` exists so you never have to parse `prompt`.** If a model takes
  structured input, or wants style in a different field from action, build it
  from `blocks` rather than splitting the prose.
- **`negative_prompt` is intent.** If the model has no negative conditioning,
  fold it into the prompt however that model prefers. If it has a different
  syntax, translate freely.
- **`last_frame` is the continuity hook.** Shot *n*'s `last_frame` and shot
  *n+1*'s opening line describe the same image on purpose. If the pipeline
  supports last-frame conditioning or image-to-video chaining, this is where to
  attach it — that is the single highest-leverage thing the engineering side can
  do for coherence, and the room has already written for it.
- **`shots[].id` is stable across rebuilds** as long as the shot keeps its
  position, so it works as a cache key or a job id.
- **Order matters.** `shots` are in narrative order and get stitched in that
  order.

## Feedback, going the other way

When a clip fails in a way that is the room's fault — a beat that can't be
rendered, a lock that produces something inconsistent, an action that needs a
cut to work — that comes back as a note on the episode or the canon entity.
The fix happens in the vault and gets rebuilt. A prompt edited downstream is a
prompt that will regress on the next build.
