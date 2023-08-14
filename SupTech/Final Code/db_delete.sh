curl --request POST http://localhost:8086/api/v2/delete?org=aptech_kor&bucket=smart_farm_bucket \
  --header 'Authorization: Token ajCjWngMkTYbvEVn7tE4NadkysKi2tQMMSZDHAdQurLWB83WrW4_QMrx29FHFEtrBMHSElvAnIYEx9ZBBPyc3A==' \
  --header 'Content-Type: application/json' \
  --data '{
    "start": "2023-01-01T00:00:00Z",
    "stop": "2023-11-14T00:00:00Z"
  }'