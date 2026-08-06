---
type: system
id: shot-grammar
title: "Shot-Grammar"
---

# Shot Grammar

What fits in ten seconds, and how to write it so it survives generation.

## The ten-second budget

A 10-second clip holds, reliably:

- **One event.** A thing happens, or a thing is revealed. Not both.
- **About eighteen spoken words**, including the silence around them.
- **One camera position.** See below.
- **Two beats of stillness** — one before the event, one after. The stillness
  is not wasted; it is what makes the event read.

A clip that needs a cut to work is two clips. This is the most common note in
the room and almost always the right one.

## Camera

Write framing, height, and whether the frame holds. That is the whole
vocabulary a writer needs:

```yaml
camera: >
  Locked-off wide at chest height, the counter across the bottom third of frame.
```

Movement is expensive and unreliable. A model asked to dolly will invent
geometry, and invented geometry does not match the clip before it. If a channel
allows movement, its [[Visual-System]] says so explicitly; otherwise assume the
camera is a bystander that does not move.

## Continuity between clips

Each shot's `last_frame` describes the image the clip ends on. The compiler
feeds it into the next clip as its opening image, automatically, so consecutive
prompts describe the same moment from both sides.

Write `last_frame` as a **still photograph**: one composition, present tense,
no action.

```yaml
last_frame: >
  The egg alone in the centre of the counter between them.
```

Good ones are specific and cheap to render — an object, a hand, a doorway. Bad
ones are motion ("she turns away") or emotion ("a look of defeat").

## Writing `action` for a machine

The `action` field is prose aimed at a model, not a reader.

| Write this | Not this |
|---|---|
| She takes out one egg and puts the carton back. | She reconsiders the carton. |
| He does not look up from the monitor. | He ignores her, exhausted. |
| A fingernail taps laminate four times. | She's getting impatient. |

Physical verbs, nameable objects, no interiority, no adjectives of mood. Mood
is the channel's job and is already in slot 2 of every prompt.

## Cast size

Two people is the practical ceiling for a clip that has to stay consistent.
Three is possible if only one moves. A crowd is a texture, not a cast — describe
it in `setting_note`, never in `cast`.
