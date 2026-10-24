---
title: One command to back up the whole homelab
date: '2026-09-18'
tags:
- homelab
- backups
- linux
- automation
summary: How I turned several manual backup procedures into a single coordinated operation
  with local validation and offsite verification.
lang: en
note_id: 2026-08-16-esta-es-una-nota-draft
---

For quite a while, creating a complete backup of my homelab meant following several separate procedures.

There are hosts, virtual machines, containers and a few services that require their own specific steps. In some cases a standby instance needs to be synchronized first. In others, a service has to be stopped temporarily before creating the backup, validating it and finally sending it to offsite storage.

It worked, but there was an obvious problem: too much of the process depended on remembering what had to be done, in which order, and what state everything was in before starting.

The idea eventually became quite simple: turn all of that into a single operation.

```bash
datacenter-backup.sh run
```

The command starts a systemd service that coordinates the complete process. This means the backup does not depend on my SSH session remaining open and can continue even after I close the terminal.

## Different systems, one process

Not every backup can be handled in the same way.

Some machines can be copied while they are running. Others need to be stopped for a few minutes. There are also services where it makes sense to synchronize a standby instance before creating its backup.

Instead of trying to force a single method onto everything, the orchestrator delegates each part of the process to small specialized scripts.

At a high level, the flow looks like this:

```text
orchestrator
    |
    +-- host configuration
    +-- remote Linux host
    +-- virtual machines
    +-- containers
    |
    +-- local validation
    |
    +-- offsite upload
    |
    +-- remote verification
```

The main script coordinates these stages and stops the process if one of them fails.

## Verify before and after

One thing I wanted to avoid was considering a backup complete simply because a command finished without errors.

The files are validated locally after they are created. Compressed archives are checked to make sure they can be read correctly, and checksums are generated for the relevant backups.

Then comes the second part: offsite storage.

The backups are uploaded to Dropbox through a container dedicated exclusively to that task. Once each transfer finishes, the local and remote files are compared again using their size and Dropbox content hash.

So the process does not end with:

```text
upload successful
```

It ends with something closer to:

```text
backup created
backup validated locally
backup uploaded
remote copy verified
```

## Returning everything to its original state

I also wanted running a backup to avoid permanently changing the state of the homelab.

Before acting on a machine or service, the process records whether it was running or stopped.

If something has to be started temporarily to perform a backup, it is stopped again afterward. If a running machine needs to be shut down for its backup, it is started again once the operation is complete.

The same idea applies to supporting services that are only required during part of the process.

The result is that the backup can temporarily modify the infrastructure, but everything should return to the same operational state once the run is finished.

## One manifest per run

Each execution also creates a manifest containing the files that belong to that backup generation.

This provides a clear reference for what was produced and what was sent to remote storage during a particular run.

It does not replace checksums or file verification, but it helps treat each backup run as a complete unit instead of a collection of unrelated files.

## The first complete run

The first real end-to-end run took a little over five hours.

During that time, the different local backups were created, validated, transferred to offsite storage and verified again on the remote side.

When the process finished, the orchestrator reported success and the machines, containers and services involved had returned to their expected state.

The main improvement is not that backups are now faster. They still take several hours and move a considerable amount of data.

The difference is that the procedure is now defined, reproducible, and has a clear beginning and end.

Before, I had several backup procedures.

Now I have one.
