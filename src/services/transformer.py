from sentence_transformers import SentenceTransformer
from redis.commands.search.query import Query
from src.common.config import get_db
import numpy as np
import sys
from flask import Flask

# Preparation
# export PYTHONPATH="/Users/mortensi/PycharmProjects/keybase/"
# python3 /Users/mortensi/PycharmProjects/keybase/src/services/transformer.py

app = Flask(__name__)
with app.app_context():
    rs = get_db().ft("document_idx").search(Query('@processable:{1}').return_field("content").return_field("processable"))
    if not len(rs.docs):
        print("No vector embedding to be processed!")
        sys.exit()

    model = SentenceTransformer('sentence-transformers/all-distilroberta-v1')
    for doc in rs.docs:
        key = doc.id.split(':')[-1]
        print("This document has no embedding: " + key)
        embedding = model.encode(doc.content).astype(np.float32).tobytes()
        doc = { "content_embedding" : embedding,
                "processable":0}
        get_db().hmset("keybase:kb:{}".format(key), doc)
        print("....done vector embedding for " + key)