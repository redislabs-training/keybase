import redis
import time
import json
from datetime import datetime
from common.config import get_db
import re

def pretty_title(title):
    return re.sub('[^0-9a-zA-Z]+', '-', title).strip("-").lower()

def get_analytics(timeseries, bucket, duration):
    ts = round(time.time() * 1000)
    ts0 = ts - duration
    data_ts = get_db().ts().range(timeseries, from_time=ts0, to_time=ts, aggregation_type='sum', bucket_size_msec=bucket)
    data_labels = [datetime.utcfromtimestamp(int(x[0]/1000)).strftime('%b %d') for x in data_ts]
    data = [x[1] for x in data_ts]
    data_graph = {}
    data_graph['labels'] = data_labels
    data_graph['value'] = data
    points = json.dumps(data_graph)
    return points