#!/bin/sh
# Download public NYC Open Data used by the siren map. Run from this folder.
set -e
mkdir -p raw
BASE=https://data.cityofnewyork.us/resource

# 1. FDNY EMS dispatches, one week (Mon 2026-09-21 .. Sun 2026-09-27)
curl -sG "$BASE/76xm-jjuj.csv" \
  --data-urlencode "\$select=incident_id,incident_datetime,first_assignment_datetime,first_activation_datetime,first_on_scene_datetime,first_to_hosp_datetime,first_hosp_arrival_datetime,incident_close_datetime,final_severity_level_code,final_call_type,zipcode,borough,incident_travel_tm_seconds_qy" \
  --data-urlencode "\$where=incident_datetime between '2026-09-21T00:00:00' and '2026-09-28T00:00:00'" \
  --data-urlencode "\$limit=200000" \
  -o raw/ems_week.csv

# 2. Modified ZIP code tabulation areas (boundaries)
curl -sG "$BASE/pri4-ifjk.geojson" --data-urlencode "\$limit=1000" -o raw/modzcta.geojson

# 3. Hospitals (NYC Facilities Database)
curl -sG "$BASE/ji82-xba5.csv" \
  --data-urlencode "\$select=facname,factype,latitude,longitude,boro" \
  --data-urlencode "\$where=factype in ('HOSPITAL','ACUTE CARE HOSPITAL')" \
  --data-urlencode "\$limit=1000" \
  -o raw/hospitals.csv

wc -l raw/ems_week.csv raw/hospitals.csv
ls -la raw
