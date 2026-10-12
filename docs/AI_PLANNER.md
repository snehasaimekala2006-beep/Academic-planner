# AI and Deterministic Study Planning Engine

## Dhanekula Institute of Engineering and Technology (DIET)
### Academic Planning & Management Platform

---

## 1. Overview

The DIET study planning engine creates personalized daily study plans for engineering students, balancing incomplete syllabus topics across available study days while strictly capping daily workloads.

---

## 2. Dual Engine Architecture

```
                       [Student Study Request]
                                  │
                                  ▼
                     [AI Optimization Enabled?]
                                  │
                 ┌────────────────┴────────────────┐
                 │ YES                             │ NO
                 ▼                                 ▼
       [LLM API Structured JSON]        [Deterministic Fallback Scheduler]
                 │                                 │
     (Valid Response?)                             │
        ┌────────┴────────┐                        │
        │ YES             │ NO (API Error/Timeout) │
        ▼                 ▼                        │
 [Validated Tasks] ──► [Run Deterministic Engine] ─┘
        │
        ▼
 [StudyPlan & StudyPlanTasks Database Persistence]
```

---

## 3. Rescheduling Missed Tasks
If a student marks a task as `MISSED` or falls behind schedule:
1. The student clicks **Reschedule Missed Tasks**.
2. Missed tasks are marked `RESCHEDULED`.
3. Tasks are redistributed across remaining future study dates, respecting daily hour limits without creating impossible schedules.
