# <img src="src/static/images/keybase.png" height="50px">

## What is Keybase?

Keybase is an Open Source Knowledge Base featuring smart searches and recommendations based on Redis Stack.

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

**RediSearch** 2.4 introduces the [Vector Similarity Search](https://redis.io/docs/stack/search/reference/vectors/) feature, which supports indexing and searching unstructured data (images, audio, videos, text etc.). Review the [release notes](https://github.com/RediSearch/RediSearch/releases/tag/v2.4.3). Keybase takes advantage of this feature to index the documents and propose recommendations, in addition to the classical RediSearch features to perform full-text searches. Analytics are managed using the **RedisTimeSeries** module, for data collection, aggregation and analysis. You can setup a Redis Stack Docker image, which includes these modules, as follows:

```
docker run -p 6379:6379 redis/redis-stack
```

> **Redis Stack Server** combines open source Redis with RediSearch, RedisJSON, RedisGraph, RedisTimeSeries, and RedisBloom. Redis Stack also includes RedisInsight, a visualization tool for understanding and optimizing Redis data.


### 3. Okta Authentication

Authentication relies on Okta. Users are cached into the Redis database in Hashes using the prefix:

```
keybase:okta:
```

Configure Okta's secret and token in the `config.py` file.

You can test the Okta integration with a [Okta Developer Edition](https://developer.okta.com/signup/).

> Note, additional basic username-password authentication method is in the works

### 4. Keybase execution

Before starting the knowledge base, you will need to configure it. Browse to `/common/config.py` and edit the information accordingly. Alternatively, you can create a shell script and `source` it. Keybase will auto-configure from environment variables. If you choose to configure via environment, write a `conf.sh` shell script:

```
#!/bin/sh
export DB_SERVICE=127.0.0.1
export DB_PORT=6379
export DB_PSW=

export OKTA_BASE=<YOUR_OKTA_DOMAIN>
export OKTA_CALLBACK_URL=http://<YOUR_WEB_DOMAIN>authorization-code/callback
export OKTA_CLIENT_ID=...
export OKTA_CLIENT_SECRET=...
export OKTA_API_TOKEN=...
```

And execute it in the session where Keybase will be started:

```
source conf.py
```


Time to start the platform with:

```
./start.sh
```

or directly with `Gunicorn`, suitable for production environments.

```
gunicorn --workers 1 --bind 0.0.0.0:5000 "wsgi:create_app()"
```

Or, to redirect logs to some place:

```
gunicorn --workers 1 --bind 0.0.0.0:5000 --log-file /var/log/keybase/rediskb.log --log-level INFO "wsgi:create_app()"
```

### 5. Indexing documents for similarity search

The indexation of documents for Similarity Search is a intensive activity that must be scheduled offline. Schedule a periodic execution of the script `transformer.py` using `cron` or a similar utility. An execution every minute is sufficient to index new documents or update the index of those documents that received an update. Using `crontab`, the task would look like:

* * * * * export PYTHONPATH=/home/<USER>/keybase/; /home/<USER>/keybasevenv/bin/python3 /home/mirko_ortensi/keybase/src/services/transformer.py > /home/<USER>/cron.log 2>&1
  
  
### 6. Using Keybase in production

Flask has a built-in web server, but it is not recommended for production usage. It is recommended to put Flask behind a web server which communicates with Flask using WSGI. 

A valid option would be to deploy Keybase together with Nginx as the web server and Gunicorn, which implements the Web Server Gateway Interface. Therefore it is possible to test Gunicorn as follows. 

```
gunicorn --workers 1 --bind 0.0.0.0:5000 "wsgi:create_app()"
```

Keybase can run on an arbitrary Redis Server configured with the RediSearch module. For a secure, reliable and data-proof solution, Redis Cloud is [recommended](https://redis.com/redis-enterprise-cloud/overview/).


## Administration

Keybase implements role-based access control. Three roles are implemented at the moment:

- Viewer: can only view and bookmark documents. When you first authenticate with Okta, you are a viewer. Only the admin can assign roles
- Editor: can create a draft, edit a draft, edit a published document. But you cannot publish a document. When editing a published document, a new review will be created, while locking other editors from creating additional reviews. Only admins can publish reviews
- Admin: can do everything. And in particular, only the admin can publish documents, create new tags and import/export data. The admin can set privileges to other users.

*Note*: The installation process does not create any super user. The first admin should be set manually in this version by accessing the database, after the first successful Okta authentication:
  
```
HSET keybase:okta:<OKTA_USER_ID> group admin
```


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
Keybase is written in Python and uses the following third-party Open Source software: Redis Stack, Toast UI Web Editor, Flask Web framework, JQuery, JQueryUI, Notify.js, Bulma CSS framework and Chart.js.
