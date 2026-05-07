#!/bin/bash
set -e

# spacy-pkuseg is a maintained fork of pkuseg with pre-built wheels
# whisperx accepts it as a drop-in replacement
pip install spacy-pkuseg

pip install -r requirements.txt
