---
note_id: 2026-05-04-aires-pulse-transaccion-pi-zeros
lang: en
title: Aires Pulse and a Transaction Between Pi Zeros
date: 2026-05-04
tags:
- raspberry-pi-zero-2w
- aires-pulse
- run-nico-ar
- nginx
- json
- home-lab
- low-tech
slug: aires-pulse-and-a-transaction-between-pi-zeros
summary: 'What started as a slightly absurd idea - making one Pi generate signals
  and another publish them - turned into Aires Pulse: a small Buenos Aires home radar
  that also started feeding run.nico.ar with real running conditions.'
---

The other day I had an idea in my head: connect two worlds that already existed, the Raspberry Pi Zero 2 Ws and my little personal sites. The idea was for one Pi Zero to generate information and the other to publish it. A kind of transaction between Pi Zeros.

The machine that generates the data is **Pipeta**, more lab than server. The one that publishes is **Pipita**, the Zero already serving [nico.com.ar](https://www.nico.com.ar "nico.com.ar"), [run.nico.ar](https://run.nico.ar "run.nico.ar"), and [zero.nico.ar](https://zero.nico.ar "zero.nico.ar") with NGINX. In between: just `rsync`, static JSON files, and a little patience.

That is how **[Aires Pulse](https://aires.nico.ar "Aires Pulse")** started.

At first it was just a dark page with a nice name and a promise: show signals from Buenos Aires in the air, the river, and the weather. Pipeta already had a previous experiment for looking at planes near Buenos Aires, so the most natural thing was to turn that information into an `aircraft.json` and show it on the site. First as numbers: how many planes, countries, speed, altitude. Then the map appeared.

With Leaflet, the site went from a card full of data to a small visual radar. The points over Buenos Aires, the Río de la Plata, the planes coming and going. All of a sudden that lab-ish idea felt like a tiny home monitoring console.

The second layer was weather. Pipeta started generating a `weather.json` with current conditions and a suggestion for when to run. It was not just about showing temperature: the point was to turn that data into something useful for deciding when to head out.

At first that information lived in [Aires Pulse](https://aires.nico.ar "Aires Pulse"). But then an obvious question showed up: if the recommendation is about running, why not use it in [run.nico.ar](https://run.nico.ar "run.nico.ar") too?

That is when the experiment got more interesting.

[run.nico.ar](https://run.nico.ar "run.nico.ar") is generated from **Pipa**, the Raspberry Pi 5. It is a static site that updates when I publish an activity or when its daily routine runs. But the weather data was coming from Pipeta and the site was hosted on Pipita. So there were three different machines, each with its own role, and the data had to travel between them coherently.

The solution was to separate the static build from the live data. [run.nico.ar](https://run.nico.ar "run.nico.ar") still lives in `/srv/data/www/run.nico.ar`, but the JSON with running conditions is published outside it, in a `live` directory, and NGINX serves it as if it were `/data/running-conditions.json`. That way, Pipa can deploy with `rsync --delete` without overwriting the data that Pipeta updates every few minutes.

Curiously, the hardest part was not the technical one, but the product one.

I had to decide what to show, how to show it, and where. The running-conditions block went through several forms before the card started answering one concrete question: **what is the best time to run?** Once the answer became easy to read, the design stopped getting in the way.

In parallel, [run.nico.ar](https://run.nico.ar "run.nico.ar") also got a split between the editorial "Next run" and the practical "Workout": one explains what makes sense to do and why, the other turns it into blocks that can be loaded manually into Garmin Connect. It is not a real integration. It is something simpler and more honest: a clear guide.

In the end, what was interesting was not just that [Aires Pulse](https://aires.nico.ar "Aires Pulse") came online, or that [run.nico.ar](https://run.nico.ar "run.nico.ar") could consume live data. What was interesting was seeing how several very small machines ended up with well-defined roles.

Pipeta observes. Pipita publishes. Pipa interprets.

All with very basic tools: NGINX, JSON, cron, `rsync`, and a bit of Python. I like that scale. It is not big infrastructure, and it does not need to be. It is just a personal ecosystem where each piece does one simple thing and does it pretty well.

And that, for now, is enough.
