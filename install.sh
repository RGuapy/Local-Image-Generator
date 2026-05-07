#!/bin/bash
set -e

# Install numpy first so pip has a concrete anchor and won't backtrack through all versions
pip install "numpy>=1.24,<3"

# spacy-pkuseg is a maintained fork of pkuseg with pre-built wheels
# whisperx accepts it as a drop-in replacement
pip install spacy-pkuseg

pip install -r requirements.txt
