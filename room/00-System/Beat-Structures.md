---
type: system
id: beat-structures
title: "Beat-Structures"
---

# Beat Structures

A post is 3–5 clips. The shapes below are the ones that survive the format.
They are starting points, not a house style — a channel is free to invent its
own, and should.

## Why the shape matters more than the joke

The first clip is competing with a thumb, and the last clip is competing with
the next video. Everything in between only has to keep someone who has already
decided to stay. Most failed posts are well-written middles with no first three
seconds and no reason to reach the end.

## Four shapes

**Ask → Refuse → Escalate → Hold** *(4 clips)*
Someone wants something; someone won't give it; the want gets worse; nobody
wins. The hold — ending without resolution — is what drives comments, which is
what drives the format. Used by [[Nothing Happens]].

**Setup → Turn → Consequence** *(3 clips)*
The tightest shape there is. Only works when the turn is genuinely a surprise,
so it burns premises fast. Best used sparingly.

**Ritual → Ritual → Ritual → Break** *(4 clips)*
Three near-identical clips establish a pattern; the fourth breaks it. The
repetition is the engine — and it costs almost nothing to write, because the
first three share a location, a camera, and most of an action. Rewards a viewer
who watches twice.

**Cold open → Escalate → Escalate → Escalate → Cut** *(5 clips)*
Pure escalation with no resolution. Each clip raises one variable and nothing
else. Needs a premise that can escalate four times without explanation.

## The first three seconds

Whatever the shape, clip one earns everything downstream. The reliable moves:

- **Start mid-action.** No one enters a room in this format. The Regular is
  already talking when the clip begins.
- **Open on the strangest true image** the episode contains, not the one that
  explains it.
- **Ask the question in dialogue** in the first clip, so the viewer knows what
  they are waiting for.

## The `beat:` field

Each shot carries a `beat:` label — `ask`, `refuse`, `escalate`, `hold`. It
does nothing at compile time; it appears in the contact sheet. Its purpose is
that a writer has to name the function of every clip, and a clip whose function
cannot be named is a clip that can be cut.
