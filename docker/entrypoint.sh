#! /bin/bash
#
port=7000
app_module="app.main:app"
# script=/dev/oar-fm-application-api/python/fm-application-api/run.py
# [ -f "$script" ] || script=/app/dist/fm-application-api/bin/run.py

[ -n "$OAR_WORKING_DIR" ] || OAR_WORKING_DIR=`mktemp --tmpdir -d _oar-rmm-python.XXXXX`
[ -d "$OAR_WORKING_DIR" ] || {
    echo "oar-rmm-python: ${OAR_WORKING_DIR}: working directory does not exist"
    exit 10
}
[ -n "$OAR_LOG_DIR" ] || export OAR_LOG_DIR=$OAR_WORKING_DIR

echo
echo "Working Dir: $OAR_WORKING_DIR"
echo "Access the RMM API at http://localhost:$port/"
echo

# Update to use uvicorn for FastAPI
echo "++ uvicorn $app_module --host 0.0.0.0 --port $port"
exec uvicorn $app_module --host 0.0.0.0 --port $port