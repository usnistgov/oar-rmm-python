#!/bin/bash
set -euo pipefail

URL="${1:-https://oardev.nist.gov/rmm/records?=&include=ediid,description,title,keyword,topic.tag,contactPoint,components,@type,doi,landingPage&exclude=_id}"
USERS="${2:-5}"
REQS="${3:-2}"
CONNECT_TIMEOUT="${CONNECT_TIMEOUT:-5}"
MAX_TIME="${MAX_TIME:-180}"

# Determine script directory and output directory
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ts="$(date +%Y%m%d_%H%M%S)"
out_base="${script_dir}/load_results"
out_dir="${out_base}/${ts}"
mkdir -p "${out_dir}"

results="${out_dir}/results.txt"
parsed="${out_dir}/parsed.txt"

echo "URL: $URL"
echo "Users: $USERS  Requests/User: $REQS"
echo "CONNECT_TIMEOUT=${CONNECT_TIMEOUT}s  MAX_TIME=${MAX_TIME}s"
echo "Output dir: $out_dir"
echo "Starting..."

run_one() {
  u=$1 r=$2
  curl -s -o /dev/null \
    --connect-timeout "$CONNECT_TIMEOUT" \
    --max-time "$MAX_TIME" \
    -w "user=$u req=$r total=%{time_total} start=%{time_starttransfer} size=%{size_download} code=%{http_code}\n" \
    "$URL"
}

touch "$results"

for u in $(seq 1 "$USERS"); do
  for r in $(seq 1 "$REQS"); do
    (
      line="$(run_one "$u" "$r")"
      echo "$line" | tee -a "$results"
    ) &
  done
done

total=$((USERS*REQS))
while jobs -p >/dev/null 2>&1; do
  done_count=$(wc -l < "$results")
  printf "\rCompleted: %d / %d" "$done_count" "$total"
  [ "$done_count" -ge "$total" ] && break
  sleep 1
done
wait
echo -e "\nAll done."

awk '/total=/{
  for(i=1;i<=NF;i++){
    if($i ~ /^total=/){t=substr($i,7)}
    if($i ~ /^start=/){s=substr($i,7)}
    if($i ~ /^size=/){z=substr($i,6)}
  }
  print t,s,z
}' "$results" > "$parsed"

AVG_TOTAL=$(awk '{st+=$1} END{if(NR)printf"%.3f",st/NR}' "$parsed")
AVG_TTFB=$(awk '{st+=$2} END{if(NR)printf"%.3f",st/NR}' "$parsed")
AVG_SIZE_MB=$(awk '{st+=$3} END{if(NR)printf"%.2f",(st/NR)/1024/1024}' "$parsed")

pct(){ p=$1; sort -g "$parsed" | awk -v p="$p" '{a[NR]=$1} END{ if(!NR){print"0"} else { idx=int((p/100)*NR); if(idx<1)idx=1; if(idx>NR)idx=NR; printf"%.3f",a[idx] } }'; }

summary="${out_dir}/summary.txt"
{
  echo "---- Summary ----"
  echo "Timestamp: $ts"
  echo "URL: $URL"
  echo "Requests: $total"
  echo "Avg Total (s): $AVG_TOTAL"
  echo "Avg TTFB  (s): $AVG_TTFB"
  echo "Avg Size  (MB): $AVG_SIZE_MB"
  echo "P50: $(pct 50)"
  echo "P90: $(pct 90)"
  echo "P95: $(pct 95)"
  echo "P99: $(pct 99)"
  echo "Results file: $results"
  echo "Parsed file:  $parsed"
} | tee "$summary"

echo "Done. All artifacts saved in: $out_dir"