---
type: character
id: {{id}}
title: "{{title}}"
created: {{date}}
channel: "[[{{channel}}]]"

# THE LOCK — the single most important line in this file.
# It is injected verbatim into every prompt this character appears in.
# Physical, unambiguous, unchanging: age, build, hair, face, wardrobe, one
# oddity a model can latch onto. No personality words — a model cannot render
# "world-weary", it can render a jaw and a jacket.
# Once clips have shipped with this lock, changing it breaks the face.
lock: >
  NAME — age, build, hair (cut, color, how it sits), face, wardrobe head to toe,
  one specific identifying detail.

# How they speak, used when a shot gives them dialogue with no delivery note.
delivery: >

# Things that are true about them but never rendered — for writers, not models.
wants: >
fears: >
running_bits: []

negative: []
---

# {{title}}

## In a sentence

## Where they came from

## What they can and can't do on camera

Physical constraints the room should respect — a character who never runs,
never raises their voice, is never seen outdoors.

## Appears in

```dataview
LIST FROM "40-Episodes" WHERE contains(string(shots), "{{title}}")
```
