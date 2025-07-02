#!/bin/bash

function show_help {
  echo "NIST RMM Python API - Development Script"
  echo ""
  echo "Usage:"
  echo "  ./start.sh                    Start the API server in development mode"
  echo "  ./start.sh test               Run the test suite"
  echo "  ./start.sh coverage           Run tests with coverage report"
  echo "  ./start.sh help               Show this help message"
  echo ""
  echo "Options:"
  echo "  -m, --module MODULE           Run tests for specific module"
  echo "  -h, --help                    Show this help message"
}

# Parse command arguments
MODE="server"
MODULE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    test)
      MODE="test"
      shift
      ;;
    coverage)
      MODE="coverage"
      shift
      ;;
    help)
      show_help
      exit 0
      ;;
    -m|--module)
      MODULE="$2"
      shift 2
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      # For backward compatibility, assume any other arg is a module
      if [[ -z "$MODULE" ]]; then
        MODULE="$1"
      fi
      shift
      ;;
  esac
done

# Ensure virtual environment is activated if it exists
if [ -d "venv" ]; then
  if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
  fi
else
  echo "⚠️ No virtual environment found at ./venv"
fi

if [ "$MODE" == "test" ]; then
  echo "🧪 Running tests..."
  if [ -n "$MODULE" ]; then
    echo "Testing module: $MODULE"
    python -m pytest "tests/$MODULE" -v
  else
    python -m pytest tests/ -v
  fi
  exit $?
elif [ "$MODE" == "coverage" ]; then
  echo "📊 Running tests with coverage..."
  if [ -n "$MODULE" ]; then
    echo "Testing module: $MODULE"
    python -m pytest "tests/$MODULE" --cov=app --cov-report=html --cov-report=term-missing
  else
    python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
  fi
  echo "✅ HTML coverage report generated in htmlcov/"
  exit $?
else
  # Original start.sh functionality
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

  echo "🚀 Starting API server..."
  uvicorn app.main:app --reload --log-level debug
fi