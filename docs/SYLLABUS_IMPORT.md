# Official Syllabus Import & Administrative Validation

## Dhanekula Institute of Engineering and Technology (DIET)
### Academic Planning & Management Platform

---

## 1. Official Curriculum Integrity Principle

Official syllabus content is treated as the institutional single source of truth. Under no circumstances should official university curriculum structures (units, topics, contact hours, credits) be fabricated or modified without validation.

---

## 2. Ingestion & Cryptographic Verification Workflow

```
[Official Syllabus PDF] 
         │
         ▼
[SHA-256 Hashing] ──────────► Stored in SyllabusSource (Immutable audit record)
         │
         ▼
[PyPDF Extraction] ─────────► Structure Parsing (Subjects, Units, Topics, Hours)
         │
         ▼
[SyllabusImport] ───────────► Status: PENDING VALIDATION (Quarantined)
         │
         ▼
[Administrator Review] ─────► Admin inspects extracted JSON & adjusts if necessary
         │
         ├───► [Action: REJECT] ──► Status: REJECTED (Archived)
         │
         └───► [Action: VALIDATE] ─► Status: VALIDATED
                                          │
                                          ▼
                      [Activated into Subjects, Units, Topics]
```

---

## 3. Administrator Review Portal
Administrators access `/syllabus/imports/<import_id>/review` to:
1. Inspect the extracted hierarchy (Units, Topics, Estimated Hours, Credits).
2. Attach validation notes reference (e.g. JNTUK Academic Senate Resolution Number).
3. Commit and activate the official curriculum into live student and faculty tracking tables.
