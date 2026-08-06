---
type: channel
id: {{id}}
title: "{{title}}"
name: "{{title}}"
network: "[[{{network}}]]"
handle: "@"
created: {{date}}

# Answer every key below before this channel compiles. Write them as camera
# instructions, not as mood — the compiler pastes them verbatim into every
# prompt, in this order, so they must read as one continuous description.
#
# Inherited from the network unless you tighten them: aspect, fps.
look:
  film: >
    TODO — Stock, format, grain, how light behaves at the edges.
  lens: >
    TODO — Focal length, height, distortion, focus behaviour.
  lighting: >
    TODO — Where the light comes from. Practical sources are more reproducible than
    described moods — a model renders "lit by a cooler" identically every time.
  palette: >
    TODO — Two colours in tension and one that anchors the frame.
  grade: >
    TODO — What happens in the shadows and the highlights.
  texture: >
    TODO — The surfaces. What this world has been touched by.
  default_camera: >
    TODO — The move used when a shot doesn't name one.

audio:
  bed: >
    TODO — The sound present in every clip on this channel.

negative: []
---

# {{title}}

> The one-line channel. What it is, for someone who will never read a second line.

## What this channel is selling

Not the product — the feeling the audience recognizes. Name it plainly.

## The three rules

Three constraints that, if broken, mean it isn't this channel anymore.

1.
2.
3.

## Where this channel sits in [[{{network}}]]

What it does that no other channel on the network does.

## The system around this file

- [[Voice-and-Tone]] — how the writing sounds
- [[Visual-System]] — the reasoning behind the `look` block
- [[Audio-System]] — the bed, and what's allowed on top of it
- [[Do-Not-Render]] — the negatives, with reasons attached
