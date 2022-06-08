import redis
from sentence_transformers import SentenceTransformer
from redis.commands.search.query import Query

pool = redis.ConnectionPool(host='127.0.0.1', port=6380, password='', db=0, decode_responses=True)
conn = redis.Redis(connection_pool=pool)

rs = conn.ft("document_idx").search(Query('@processable:{1}').return_field("name").return_field("processable"))
for doc in rs.docs:
    print(doc.id.split(':')[-1])