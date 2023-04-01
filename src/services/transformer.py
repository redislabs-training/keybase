from sentence_transformers import SentenceTransformer
from redis.commands.search.query import Query
from src.document.document import Document

import numpy as np
import sys
from flask import Flask

# In production uncomment this line and set the keybase folder path
# sys.path.append('/Users/mortensi/PycharmProjects/keybase/')
from src.common.utils import get_db

# Or set the PYTHONPATH environment variables
# export PYTHONPATH="/Users/mortensi/PycharmProjects/keybase/"
# python3 /Users/mortensi/PycharmProjects/keybase/src/services/transformer.py

app = Flask(__name__)

with app.app_context():
    rs = get_db().ft("document_idx"). \
        search(Query('@processable:[1,1]').
               return_field("content").
               return_field("processable"))
    if not len(rs.docs):
        print("No vector embedding to be processed!")
        sys.exit()

    model = SentenceTransformer('sentence-transformers/all-distilroberta-v1')
    for doc in rs.docs:
        pk = doc.id.split(':')[-1]
        document = Document.get(pk)
        print("This document has no embedding: " + pk)
        embedding = model.encode(document.currentversion.content).astype(np.float32).tobytes()
        doc = {"content_embedding": embedding,
               "name": document.currentversion.name,
               "state": document.state,
               "privacy": document.privacy}
        get_db().hset("keybase:vss:{}".format(pk), mapping=doc)
        document.processable = 0
        document.save()
        print("....done vector embedding for " + pk)
