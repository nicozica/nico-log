---
note_id: 2026-03-09-pacer-strava-brief-builder
lang: en
title: 'Pacer: From Screenshots to a Clean Brief for ChatGPT'
date: 2026-03-09
tags:
- pacer
- strava
- running
- raspberry-pi
- nodejs
- automation
- argensonix-labs
slug: pacer-from-screenshots-to-a-clean-chatgpt-brief
summary: I built Pacer, a local app that pulls my activities from Strava, summarizes
  recent load, and lets me generate a simple brief to pass to ChatGPT without relying
  on screenshots or huge blocks of text.
---

Today **Pacer** was born, a small app built for one very specific thing: **stop handing screenshots to ChatGPT and start giving it useful context**.

The idea came from a very simple need. When I want to review how I’ve been training and decide what to do the next day, I do not need nine screenshots, or a novel explaining everything, or to rely on memory to remember what I did three days ago.

I need this:

- what I have been doing lately
- how much I ran
- whether I rode the bike
- whether I did strength work
- how I feel today

And that’s it.

### The underlying problem

For a long time the flow was more manual than anything else.

Look at Garmin.
Look at Strava.
Take screenshots.
Send them.
Explain how things feel.
Summarize again by hand.

It worked, yes. But there was too much friction.

What was interesting was that, once I tried to automate it, a few truths showed up pretty quickly:

- **Strava** works much better as a data source than as a website to scrape
- **Garmin** is still better as a watch and training ecosystem than as an open platform for personal integrations
- **Playwright** is good, but it did not make sense to make it the star of something Strava already solved better through an API

### What Pacer ended up being

Pacer became a simple and much saner tool:

- it pulls my latest activities from the **Strava API**
- it stores everything in JSON
- it serves a tiny web app
- it automatically summarizes recent load
- it lets me fill in just a few manual fields
- it generates text ready to copy or download

I then pass that text to ChatGPT and the back-and-forth gets much cleaner.

### What the app shows

For now Pacer already summarizes a few useful things:

- last activity
- last run
- last ride
- summary of the last 7 days
- running volume
- cycling volume
- strength and workout sessions

And it also has a very short manual block to fill in:

- overall feeling
- legs
- sleep
- extra note

That alone lowers the friction a lot.

### The most important part

The point was not to make another “fitness” app.

The point was to build **a bridge between my data and a useful conversation**, to help me answer one concrete question:

**what should I do tomorrow?**

In that sense, Pacer already does its job.

### What went well

A few things ended up fitting together better than expected:

- the Strava fetch works
- the JSON is useful
- copy to clipboard / download txt make a lot more sense than they seemed to
- I no longer depend on screenshots

### Next step

Polish it without making it complicated:

- a more compact brief
- local persistence for the manual fields
- a more polished deploy flow

But the important part has already happened.

**Pacer stopped being an idea and started being useful.**
