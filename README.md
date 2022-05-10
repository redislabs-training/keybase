# <img src="src/static/images/keybase.png" height="50px">

keybase is a Redis based knowledge base, substantially a markdown editor to store and search documents.

## Preparation

In order to prepare your Python setup, create a virtual environment:

```
python3 -m venv keybasevenv
source keybasevenv/bin/activate
python3 -m pip install --upgrade pip
```
Then, install the requirements:

```
pip3 install -r requirements.txt
```

## The Redis database

RediSearch 2.4 introduces the [Vector Similarity Search](https://redis.io/docs/stack/search/reference/vectors/) feature, which supports indexing and searching unstructured data (images, audio, videos, text etc.). Review the [release notes](https://github.com/RediSearch/RediSearch/releases/tag/v2.4.3). keybase takes advantage of this feature to index the documents and propose recommendations, in addition to the classical RediSearch features to perform full-text searches.
You can test against a Docker Hub image, such as:

```
docker run -p 6379:6379 redislabs/redisearch:2.4.3
```

Then, configure the Redis database credentials in `config.py`. Finally, create the index (documents are stored in Hashes).

```
FT.CREATE document_idx ON HASH PREFIX 1 "keybase:kb" SCHEMA name TEXT content TEXT creation NUMERIC SORTABLE update NUMERIC SORTABLE content_embedding VECTOR FLAT 6 TYPE FLOAT32 DIM 768 DISTANCE_METRIC COSINE
```

Time to start the platform:

```
./start.sh
```
