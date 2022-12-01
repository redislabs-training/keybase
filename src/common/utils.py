import redis
import time
import json
from datetime import datetime

import shortuuid

from src.common.config import get_db
import re


class ShortUuidPk:
    def create_pk(self) -> str:
        shortuuid.set_alphabet('123456789abcdefghijkmnopqrstuvwxyz')
        return shortuuid.uuid()[:10]


def pretty_title(title):
    return re.sub('[^0-9a-zA-Z]+', '-', title).strip("-").lower()


def get_analytics(timeseries, bucket, duration):
    ts = round(time.time() * 1000)
    ts0 = ts - duration
    data_ts = get_db().ts().range(timeseries, from_time=ts0, to_time=ts, aggregation_type='sum',
                                  bucket_size_msec=bucket)
    data_labels = [datetime.utcfromtimestamp(int(x[0] / 1000)).strftime('%b %d') for x in data_ts]
    data = [x[1] for x in data_ts]
    data_graph = {'labels': data_labels, 'value': data}
    points = json.dumps(data_graph)
    return points
