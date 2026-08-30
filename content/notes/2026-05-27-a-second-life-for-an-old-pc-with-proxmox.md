---
note_id: 2026-05-27-pc-segunda-vida-proxmox
lang: en
title: A Second Life for an Old PC with Proxmox
date: 2026-05-27
tags:
- proxmox
- home-lab
- linux
- virtualization
- fedora
- tailscale
- kubernetes
- low-tech
slug: a-second-life-for-an-old-pc-with-proxmox
summary: 'An old PC gathering dust turned into the perfect excuse to build a Proxmox
  lab: try distros, understand virtualization better, play with old disks, and keep
  production separate from experiments.'
---

I had an old PC gathering dust in a box in a corner of my room. For years it was my main machine: an AMD FX 8300, an ASUS motherboard, 16 GB of RAM, a Gigabyte 2 GB graphics card, and a pretty decent power supply. At the time it ran Windows 10, I used it hard for years, and it always responded well.

After I built my current PC, installed Fedora, and got used to working in Linux every day, the old machine fell off the map. It was not broken, not useless, it had just lost its place.

The other day I pulled it out of the box, cleaned it, changed the thermal paste, powered it on, and it booted perfectly. It took memory, showed video, and was left waiting for the one thing it still did not have: a disk to boot from.

That is when the idea came to give it a second life, but not as a main PC or as a replacement for any current server. The idea is much simpler: turn it into a Proxmox lab to power on whenever I want to test something, break a VM, install a new distro, or practice infrastructure without touching anything important.

I like that separation. My production server has to be boring and stable. I do not want to use it for weird experiments or for trying things that might break. For that it makes much more sense to have a separate machine, old but still capable, where making mistakes is not a problem.

The hardware is not modern, but it is pretty fun as a lab. A 960 GB SATA SSD for Proxmox and the main VMs, a 1 TB WD Blue disk for test backups or secondary storage, and an old laptop mechanical drive to experiment on without fear. It even has a DVD burner, which is completely unnecessary in 2026, but precisely for that reason kind of charming in a home lab.

The only less polished part is the network. I do not have direct Ethernet in that room, so the plan is to use a WiFi repeater with a Gigabit Ethernet port. The repeater connects to the home WiFi and the PC sees it as a normal wired connection. For Proxmox that is much cleaner than relying on a direct WiFi card inside the host.

I also want to try Wake on LAN. The machine has already worked before with a magic packet, so the idea is to be able to turn it on remotely from a Raspberry Pi that stays on all the time with Tailscale. In practice it would be pretty simple: I connect from outside to the home network, send the magic packet, the PC boots, I get into the Proxmox panel, and I start the VM I need.

What excites me most is not raw power, but the kind of things I can learn there. I want to try Fedora Server, openSUSE, Arch Linux, Omarchy, plain Debian, and some distros that were left out on smaller machines. I would also like to play with Proxmox Backup Server, practice snapshots, do real restores, and understand better how to organize VM templates.

Another idea that interests me is trying K3s, a lightweight version of Kubernetes. Not because I want to turn my house into a datacenter, but because as a designer and UX engineer it helps to understand better what happens after an interface stops being a design or a prototype.

There is a path that often stays a bit invisible from the design side: frontend, build, container, deploy, service, ingress, logs, rollback. Being able to walk that flow on a small scale, with a simple app or an internal dashboard, seems like a very concrete way to learn. I do not need huge infrastructure. I need a place where I can test things, see what happens, and roll back without fear.

The machine can also help me organize my home ecosystem better. Today I have a main PC for work, a server that keeps real services running, a Raspberry Pi for staging and remote access, another one for lightweight static sites, and a few smaller machines for tests. What was missing was a clear place to break things without mixing them with production.

That would be this PC's role: on-demand lab. After that will come the distros, Kubernetes, the old disks, the templates, and all the other ideas.

I like it because I am not buying a new PC or complicating something that already works. I am recovering hardware I already had and giving it a much clearer role than before. The old PC does not come back as a main machine, but as an all-terrain Linux lab.
