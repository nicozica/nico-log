---
note_id: 2026-08-28-cuando-una-herramienta-deja-de-ser-un-experimento
lang: en
title: When a Tool Stops Being an Experiment
date: '2026-08-28'
tags:
- automation
- drupal
- devops
- ai
slug: when-a-tool-stops-being-an-experiment
summary: How a banner-visibility automation grew into a small campaign system coordinating
  content, markets, schedules, and contingencies.
---

A few weeks ago a concrete problem showed up at work: we had to publish and take down a banner in dozens of markets, at a specific time, inside Drupal.
Doing it manually was possible. It was also exactly the kind of task that makes you ask: **why are we doing this by hand?** That is how Banner Scheduler was born.
The first version had a pretty narrow goal: schedule visibility changes. Pick the markets, define a date, and let the tool do the work when the time came. But a more interesting problem showed up quickly: visibility was only part of the story.
What happens when the banner content changes too? What do we do with different translations? How do we schedule several changes during a campaign? How do we keep Drupal from becoming the place where the content lives again? What happens if the site is temporarily under maintenance when it is time to run a change?

That is where the project started to change. Today the Scheduler works together with **Atlas**, another internal tool we use as the source of truth for content and translations. The split ended up pretty clear:

* Atlas knows **what content should exist**.
* The Scheduler knows **when it has to change and when it should be visible**.
* Drupal stays the final destination, not the place where the whole process is managed.

A campaign can be loaded from a spreadsheet, validate its markets and schedules, prepare the different content changes, and generate the jobs that will run later. There is also a small sequence I really liked: **check, apply, arm**. First check that what we want to do makes sense. Then create the campaign. And only then arm the jobs that can touch production.

The schedules for the different markets are normalized, the actions are logged, and the worker takes care of executing what was scheduled. If certain temporary conditions prevent a change from happening, there are retries instead of immediately assuming everything failed. All of that ended up paired with an interface where you can see campaigns, upcoming changes, recent activity, and the state of each operation.

This week the small milestone that justified writing all this happened: **we launched the first real campaign.**
It was no longer a test, a dry run, or specially prepared data for building the tool. There was real content, real schedules, and real changes that actually had to happen.

And it worked. Maybe what I like most about this project is that it did not start from a giant specification or the idea of building a “platform”.
It started by looking at a pretty tedious task and thinking: **this could be done better.** The rest appeared question by question. And there are probably still quite a few questions left.
