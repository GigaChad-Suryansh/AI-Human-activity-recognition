# Space Experiment AI

SIH prototype for offline Human Activity Recognition and experiment-sequence validation.

## Current MVP

- Responsive mission-control dashboard
- Live browser camera input
- Local video-file input
- Experiment state machine for a predefined 6-step protocol
- Correct / skipped-sequence validation
- Browser voice alerts
- Timestamped JSONL export
- Camera snapshot export
- Offline-first UI; no cloud inference or API key required
- GitHub Pages deployment workflow

## Demo flow

1. Open the dashboard.
2. Click **Start Experiment** and allow camera access.
3. Use the controls / state transitions to demonstrate step validation.
4. A protocol violation triggers a voice alert.
5. Export `events.jsonl` for the structured experiment record.

## Important

This repository is currently the **working application shell / MVP**, not the final trained AI model. The browser UI is designed to receive the real edge-AI outputs later: object detection, pose estimation, hand-object interaction and temporal activity recognition. The experiment state machine then validates the predefined sequence.

The production architecture should remain:

`Camera → Object Detection → Pose / Hand-Object Interaction → Temporal HAR → Experiment State Machine → Alert + Log + GUI`

## Deployment

GitHub Actions deploys the static application to GitHub Pages on pushes to `main`. In the repository settings, Pages should use **GitHub Actions** as the source.
