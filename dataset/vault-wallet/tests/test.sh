#!/bin/bash
set -u
mkdir -p /logs/verifier
export D2C_CLIP_CACHE=/opt/clip
PYTHONPATH=/tests python -m d2c.grade.verify
