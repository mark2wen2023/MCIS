# Versioned Skill UI slice

Changed extractionWorking hostPort/ExtractionWorking, workingArchive hostPort/WorkingArchive. Both consume the same strict Pi result parser. Execution v1 has no SkillRef and is displayed as not recorded, without inference/backfill. Execution v2 requires exact skillRef {id, version, contentDigest}; profile, ID syntax, bounded version, lowercase digest and existing trace checks remain strict. Extra fields and changed historical execution fingerprints are rejected.

No registry lookup, fetching, link or execution permission is conferred by a reference, especially for historical imports. Unknown structurally valid IDs retain their original text with neutral Skill version labels, not an inferred professional skill name. Engineering checks are not professional certification. No changes to routes or production configuration.

Checks: pi-skill-ui.tsx 26/26; existing extraction-working-pi 30/30 and working-archive-pi 28/28; strict TypeScript passed. All fixtures, no provider calls.

pi-public-ui-live.tsx now verifies v2 SkillRef from protected persisted read through rendered review, remount, export, import and historical view, preserving all original quotes/citations. Full explicit fixture run 7dac16e4-0def-49f8-ba68-60682d6921f8 accepted after cleanup acknowledgement and child exit 0: 3 mocked model rounds, 2 tools, 1 proposal, 1 citation, zero provider requests. HappyDOM, not browser E2E; scripted review, not a human review. No fact activation. Old live v1 run does not verify this v2 slice.

Source frozen for independent review; no commit, push, deployment or real model request by this task.
