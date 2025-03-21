#!/bin/bash


# Test if the remote URL is reachable first
if [ -n "$REMOTE_CONFIG_URL" ]; then
  echo "Testing connection to config URL: $REMOTE_CONFIG_URL"
  curl -s --connect-timeout 3 "$REMOTE_CONFIG_URL" > /dev/null
  if [ $? -eq 0 ]; then
    echo "✅ Remote config URL is reachable"
  else
    echo "⚠️ Warning: Cannot reach remote config URL: $REMOTE_CONFIG_URL"
    echo "Will fall back to local configuration"
  fi
fi

uvicorn app.main:app --reload --log-level debug
