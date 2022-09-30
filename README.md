# <img src="src/static/images/keybase.png" height="50px">

## What is keybase?

Keybase is an Open Source Knowledge Base featuring smart searches and recommendations based on Redis Stack. Using this software:

- Create and edit documents using a WYSIWYG Markdown editor
- Browse, search, and bookmark Knowledge Base articles
- Get recommendations for similar documents
- Organize and research content using labels
- Okta authentication integrated
- Role-Based Access Control


## Installation

In order to install Keybase, please pay attention to the following sections.

### 1. Python environment

prepare your Python setup, create a virtual environment:

```
python3 -m venv keybasevenv
source keybasevenv/bin/activate
python3 -m pip install --upgrade pip
```
Then, install the requirements:

```
pip3 install -r requirements.txt
```

### 2. The Redis database

RediSearch 2.4 introduces the [Vector Similarity Search](https://redis.io/docs/stack/search/reference/vectors/) feature, which supports indexing and searching unstructured data (images, audio, videos, text etc.). Review the [release notes](https://github.com/RediSearch/RediSearch/releases/tag/v2.4.3). keybase takes advantage of this feature to index the documents and propose recommendations, in addition to the classical RediSearch features to perform full-text searches. You can test against a Docker Hub image, such as:

```
docker run -p 6379:6379 redislabs/redisearch:2.4.3
```

1. Configure the Redis database credentials in `config.py`. 
2. Create the index (documents are stored in Hashes).

```
FT.CREATE document_idx ON HASH PREFIX 1 "keybase:kb" SCHEMA name TEXT content TEXT creation NUMERIC SORTABLE update NUMERIC SORTABLE state TAG owner TEXT processable TAG tags TAG content_embedding VECTOR HNSW 6 TYPE FLOAT32 DIM 768 DISTANCE_METRIC COSINE
```

3. Create also the index for users.

```
FT.CREATE user_idx ON HASH PREFIX 1 "keybase:okta" SCHEMA name TEXT group TEXT
```

4. Finally, consider that Vector Similarity syntax will need the following syntax dialect. Then set it:

```
FT.CONFIG SET DEFAULT_DIALECT 2
```

### 3. Okta Authentication

Authentication relies on Okta. Users are cached into the Redis database in Hashes using the prefix:

```
keybase:okta:
```

You can test the Okta integration with a [Okta Developer Edition](https://developer.okta.com/signup/).

### 4. Keybase execution

Time to start the platform with:

```
./start.sh
```

Or using WSGI and gunicorn:

```
gunicorn --workers 1 --bind 0.0.0.0:5000 "wsgi:create_app()"
```

## Role Based Access Control

Three roles are implemented at the moment:

- Viewer: can only view and bookmark documents. When you first authenticate with Okta, you are a viewer. Only the admin can assign roles
- Editor: can create a draft, edit a draft, edit a published document. But you cannot publish a document. When editing a published document, a new review will be created, while locking other editors from creating additional reviews. Only admins can publish reviews
- Admin: can do everything. And in particular, publish documents and new versions

## Troubleshooting

If after installing `sentence_transformers` you fail to start the application and get:

```
ModuleNotFoundError: No module named 'sentence_transformers'
```

Or, you fail to install it and `pip install sentence_transformers` fails with "Killed", you may be running out of RAM memory. If that is the case, try to install `sentence_transformers` using:

```
pip install sentence_transformers --no-cache-dir
```

## Components
Keybase is written in Python and uses the following third-party Open Source software: Redis Stack, Toast UI Web Editor, Flask Web framework, JQuery, JQueryUI, Notify.js, Bulma CSS framework. 