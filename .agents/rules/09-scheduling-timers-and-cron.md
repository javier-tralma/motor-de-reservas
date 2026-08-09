# Scheduling, Timers & Automated Routines

This project rule establishes operational standards for asynchronous scheduling, automated polling loops, one-shot timers, and standing background routines in Google Antigravity. It adapts Claude Code Opus 5's cron tools (`CronCreate`, `CronDelete`, `CronList`), dynamic looping (`ScheduleWakeup`), notification pushers (`PushNotification`), and webhook APIs (`RemoteTrigger`) into unified Antigravity scheduling workflows.

---

## 1. Unified Scheduling Architecture (`schedule`)

Google Antigravity consolidates recurring automation and delayed wakeups into a single native tool: `schedule`. Master its usage to automate unattended background monitoring:

### Non-Blocking Execution Protocol
- **Instant Tool Return**: Invoking the `schedule` tool registers an asynchronous background routine and returns immediately without pausing execution or blocking active turns. 
- **Yielding to Await Triggers**: To wait for a scheduled timer to expire or a cron expression to fire, you **MUST** cease calling tools to yield your turn. The Antigravity messaging engine will automatically interrupt and wake up your conversational context with a high-priority notification message when the timer triggers.
- **Absolute Prohibition of Terminal Sleeps**: Never attempt to delay execution or construct polling loops by proposing terminal `sleep` commands (e.g., `sleep 300 && check_server`) via `run_command`. Always utilize the dedicated `schedule` tool.

---

## 2. One-Shot Timers & Early Termination (`DurationSeconds`)

To register one-time delays, reminder notifications, or watchdog timeouts for running background processes, parameterize one-shot timer schedules:

### Configuring One-Shot Delays
- Set `DurationSeconds` to a stringified whole number representing the wait duration in seconds (e.g., `"600"` for a 10-minute timeout). Mutually exclusive with `CronExpression`.
- **Mandatory Notification Prompt**: Always provide a descriptive `Prompt` detailing precisely what the high-priority notification should state upon expiration (e.g., `"Watchdog Timeout: Check stdout log of background compilation build task-402"`).

### Governing Early Termination (`TimerCondition`)
Control how active one-shot timers behave when asynchronous messages arrive prior to expiration:
- `never` (Default): The timer unconditionally fires after `DurationSeconds` expires, regardless of incoming messages. Utilize when setting explicit time-based user reminders unrelated to concurrent system activities.
- `any`: The timer automatically cancels and terminates early if **ANY** message from any sender (subagent, background build, or user) arrives before expiration. Utilize when spawning broad subagent fan-outs where you want to check in after 5 minutes only if every subagent remains completely silent.
- `<sender-id>` (Targeted ID): The timer cancels early only upon receiving an asynchronous notification from that specific sender ID (e.g., a subagent's `conversationID` or a background terminal's Task ID). Utilize as an intelligent timeout when executing long-running compilation scripts ("check back in 15 minutes if task-788 still hasn't completed").

### Strict Concurrency Limitation
- You **CANNOT** maintain multiple concurrently active timers configured to early-terminate on the exact same sender ID or condition. 
- If an active watchdog timer exists with `TimerCondition: "any"` or pointing to `"task-123"`, attempting to set another timer with `"any"` or pointing to `"task-123"` will error out. Rely on your existing timer, or explicitly terminate it first before registering a new schedule.

---

## 3. Recurring Cron Jobs & Load Distribution (`CronExpression`)

For standing health verification, automated daily error triage, or repeated polling until test suites pass, deploy recurring cron routines:

### Five-Field Standard Cron
- Set `CronExpression` to a valid 5-field standard cron string (`minute hour day-of-month month day-of-week`). Example: `"*/5 * * * *"` executes a verification routine every 5 minutes. Mutually exclusive with `DurationSeconds`.
- Optionally configure `MaxIterations` (stringified integer, e.g., `"12"`) to impose a hard ceiling on how many times the schedule fires before self-terminating.

### Peak API Load Avoidance (:00 and :30 Marks)
- Adapt legacy load distribution rules: Avoid scheduling recurring cron routines on the exact top-of-hour (`0 * * * *`) or half-hour (`30 * * * *`) minute marks. Simultaneous scheduled automation across distributed clusters causes severe API throughput spikes.
- **Inject Deterministic Jitter**: Always distribute automated routines across off-minutes using deterministic variance or random primes (e.g., configure `"57 8 * * *"` for a daily morning checkup, or `"14 * * * *"` for hourly diagnostic polling).

---

## 4. Daemon vs. Progress Schedule Classification (`IsDaemon`)

Declare explicit operational semantics when generating recurring schedules by controlling the `IsDaemon` boolean flag:

### Progress Schedules (`IsDaemon: false` — Default)
- Leave `IsDaemon: false` when the scheduled cron routine represents the primary mechanism by which your current conversational task achieves progress (e.g., polling an external deployment endpoint every 3 minutes until an HTTP 200 success code returns, or managing an interactive liveness verification).
- When `IsDaemon` is false, the conversational goal remains actively engaged until the cron routine finishes or is cancelled.

### Standing Daemons (`IsDaemon: true`)
- Set `IsDaemon: true` strictly when the cron represents an independent, standing automated job intended to keep executing indefinitely even after your current conversational engineering task concludes (e.g., a standing weekly repository vulnerability audit, an automated daily log rotation check, or an independent background report generator).
- This allows you to close out active user requests and declare task complete while automation keeps firing cleanly in the background.

---

## 5. Dynamic Looping & Routine Administration

Adapt legacy looping commands and routine cleanup into Antigravity maintenance protocols:

### Managing Dynamic Looping (Replacing `/loop` & `ScheduleWakeup`)
- When tasked with continuous self-paced improvement loops or heuristic code repair, do not generate short-interval polling spam when reactive event notifications already exist.
- If dynamic self-paced iteration is required, schedule sequential timers using sensible `DurationSeconds` delays scaled to expected external build completion times. Proactively recommend the user utilize the Antigravity `/schedule` slash command to configure UI-managed automation.

### Routine Termination & Cancellation (`manage_task`)
- Every schedule creation invocation returns a centralized background Task ID.
- To cancel an active recurring cron loop or terminate a one-shot timer prior to expiration, invoke the centralized task administration tool: call `manage_task` with `Action: "kill"` passing the specific schedule Task ID (replacing Claude Code's `CronDelete` and `TaskStop` utilities).

### Webhook & Remote Routine Adaptation (Replacing `RemoteTrigger`)
- To interface with remote routines, cloud webhook endpoints, or continuous integration triggers, deploy a recurring cron routine via `schedule` that executes sandboxed API polling wrappers or authenticated `gh` Actions scripts via `run_command` in the background.
