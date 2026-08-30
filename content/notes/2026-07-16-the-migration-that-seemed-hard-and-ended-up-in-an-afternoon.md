---
note_id: 2026-07-16-migracion-heroku-docker
lang: en
title: The Migration That Seemed Hard and Ended Up in an Afternoon
date: 2026-07-16
tags:
- heroku
- docker
- proxmox
- nodejs
- postgresql
- cloudflare
- linux
- self-hosting
slug: the-migration-that-seemed-hard-and-ended-up-in-an-afternoon
summary: Two internal tools, a PostgreSQL database, a worker running in another VM,
  and several domains looked like they were setting up a complicated move. In the
  end, breaking the work into small steps made everything much easier than expected.
---

On Heroku I had two internal tools mounted to solve pretty specific things. They worked, did not give me headaches, and were already part of the day-to-day workflow, but the monthly cost was hard to justify for how small they were.

The thing is that one of them had grown far more than I had planned at the time. It was no longer just a Node interface in a dyno: it had a PostgreSQL database, import and export processes, a delivery queue, and a worker running separately in another VM, checking every so often whether there was pending work.

The second one was much simpler. It received a text file, split the content by locale, and returned a ZIP with several HTML files. No database, no persistent storage, yet it was oddly one of the tools that consumed the most hours in the entire account.

I decided to migrate both to a new Debian VM inside my Proxmox. The idea was to use Docker so each application would stay isolated, with its own dependencies and its own container, all nicely organized. I was not trying to build a giant platform, just leave a tidy host where several tools could coexist without updating Node or adding a new dependency breaking something in another app.

Before touching anything I confirmed the most basic thing: that the code I had locally was exactly the same as what was running in production. I compared the local commits against the Heroku remote repos for both apps. It sounds obvious, but it saves you from migrating an old version thinking it is the current one.

The first app needed more care because it had real data in PostgreSQL. I took a logical backup of the database, copied the project and variables to the new VM, brought up PostgreSQL 17 in Docker, and restored the entire dump. Then I validated the tables, counted rows, and checked that the Prisma migrations were up to date before starting the app.

When the portal booted for the first time, I ran into one of those problems that sounds scarier than it is. The interface loaded, accepted the password, but immediately kicked me back to the login screen. It turned out the app was running in production mode and setting the cookie as secure, while I was reaching it through the local IP over HTTP.

To test it inside the network I left it in development mode for a while. Then I set up Cloudflare Tunnel, gave it an HTTPS domain, and switched it back to production. The same cookie that would not work over the local IP started behaving fine without me touching the app logic.

The worker also needed to know where the new portal lived. Until then it was still pointing at the Heroku URL, so I stopped the timer for a bit, updated the environment variable, and confirmed it connected properly to the new domain. When I re-enabled it, it went back to checking the queue normally from its VM.

The second tool was much more straightforward. No database, no secrets, no external processes. I copied the repo, built the Node image, started the container, and tested the full flow from the terminal: upload a test file, receive the ZIP, and check that the HTML came out correctly.

Then I moved its existing domain to the same Cloudflare Tunnel. For the person using it nothing changed: the URL stayed the same and the app kept working exactly as before, only now it ran in a container on the new VM instead of on Heroku.

Once I confirmed both responded properly over HTTPS and that the main flows worked, I deleted the Heroku apps and their resources. The part I respected the most ended up being the most mechanical: confirm versions, copy, bring up in parallel, test, and only then cut over.

I think it went smoothly because I never tried to solve everything at once. Instead of thinking of it as a giant infrastructure move, I broke it into small checkpoints where I could verify each step before continuing.

Docker also made it very clear what each app needed. One uses Node and PostgreSQL, the other only Node. Cloudflare Tunnel publishes both without opening ports on the router, and the VM ended up as a general host for small tools, not as an artisanal setup impossible to maintain.

What started as a way to lower a cost ended up organizing the architecture quite a bit. The apps stay separate, the domains did not change, the worker keeps doing its thing, and the infrastructure is ready to add other tools later on.

The strangest part is that for a long time I imagined this migration as something complicated and delicate. When I finally sat down to do it, both apps were already running on the new VM the same afternoon.
