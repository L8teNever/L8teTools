#!/bin/bash
# Post-install script for additional setup

# Download spacy German language model (optional, for name recognition)
python -m spacy download de_core_news_sm || echo "Spacy model download failed (optional)"

echo "Setup complete!"
