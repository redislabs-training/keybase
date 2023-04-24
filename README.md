# <img src="src/static/images/keybase.png" height="50px">

## Keybase, the real-time Knowledge Base

Keybase is an Open Source Knowledge Base featuring smart searches and recommendations based on [Redis Stack](https://redis.io/docs/stack/about/).

- Create and edit documents using a WYSIWYG Markdown editor
- Browse, search, and bookmark Knowledge Base articles
- Get recommendations for similar documents
- Organize and research content using labels and categories
- Password-based and Okta-based authentication integrated
- Role-Based Access Control
- Public view and custom templates


## Quickstart

In order to install and run the knowledge base, please pay attention to the following instructions.

### 1. The Redis database

Keybase is backed by a Redis Stack database. You can set up a Redis Stack Docker image as follows:

```
docker run -p 6379:6379 redis/redis-stack
```

> **Redis Stack Server** combines open source Redis with RediSearch, RedisJSON, RedisGraph, RedisTimeSeries, and RedisBloom. Redis Stack also includes RedisInsight, a visualization tool for understanding and optimizing Redis data.

### 2. Installation

prepare your Python setup, create a virtual environment:

```
python3 -m venv kvenv
source kvenv/bin/activate
python3 -m pip install --upgrade pip
```

Then, install the software

```
git clone https://github.com/redislabs-training/keybase.git
cd keybase
pip install -e .
```

Now configure the environment and run using `gunicorn`. 

```commandline
export DB_SERVICE="localhost" DB_PORT=6379 DB_PWD="" CFG_AUTHENTICATOR="auth" CFG_THEME="default"
gunicorn --workers 1 --bind 0.0.0.0:5000 --log-level debug --capture-output --error-logfile ./gunicorn.log "wsgi:create_app()"
```

Connect to a Redis database and create the first administrator:

```commandline
HSET keybase:auth:admin username admin password 8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918 status enabled group admin given_name "Administrator" name "Administrator"
```

Finally, point your browser to the knowledge base:

```commandline
http://localhost:5000/
```

### 3. Okta Authentication

You can configure the authentication to use Okta. Just set `CFG_AUTHENTICATOR="okta"`, and configure Okta's secret and token in a `.env` file under `src/common` or via system environment variables.

```commandline
export OKTA_BASE=<YOUR_OKTA_DOMAIN>
export OKTA_CALLBACK_URL=http://<YOUR_WEB_DOMAIN>authorization-code/callback
export OKTA_CLIENT_ID=...
export OKTA_CLIENT_SECRET=...
export OKTA_API_TOKEN=...
```

Okta users are cached into the Redis database in Hashes using the prefix:

```
keybase:okta:
```

You can test the Okta integration with a [Okta Developer Edition](https://developer.okta.com/signup/).

> Note, additional basic username-password authentication method is in the works


## Keybase execution in a Docker container

This repository comes with a Dockerfile you can use to generate an image and start it. Use the following commands.

Build image from Dockerfile

```
docker build -t keybase:v1 .
```

Start the knowledge base

```commandline
docker run -d --cap-add sys_resource --env DB_SERVICE=<database_host> --env DB_PORT=<database_port> --env DB_PWD=<default_user_password> --env CFG_AUTHENTICATOR="auth" --env CFG_THEME="default" --name kb -p 5000:8000 keybase:v1
```


## Recommendations based on Vector Similarity Search (VSS)

Recommendations of semantically similar documents are proposed, the feature uses [Vector Similarity Search](https://redis.io/docs/stack/search/reference/vectors/). 
VSS is based on the generation and storage of vector embeddings. Provided vector generation from the content is an intensive activity, the generation must be scheduled offline. 

Schedule a periodic execution of the script `transformer.py` using `cron` or a similar utility. An execution every minute is sufficient to index new documents or update the index of those documents that received an update. 
Using `crontab`, the task would look like:

```
* * * * * export PYTHONPATH=/home/<USER>/keybase/; /home/<USER>/keybasevenv/bin/python3 /home/<USER>/keybase/src/services/transformer.py > /home/<USER>/cron.log 2>&1
```

It is also possible to subscribe to the Redis Stream `keybase:events` to capture events published by the knowledge base.
Currently, an event is published when a document is added or updated, so a client application that detects a relevant event, can recalculate the vector embedding and store it.

You can create a consumer group:

```commandline
XGROUP CREATE keybase:events vss_readers $
```

And then use your favorite client to read from the stream the newest events with `XREADGROUP` and manage the stream as usual, with `XACK`, `XPENDING` and `XCLAIM`.

```commandline
XREADGROUP GROUP vss_readers default COUNT 1 STREAMS keybase:events >
1) 1) "keybase:events"
   2) 1) 1) "1682327824341-0"
         2) 1) "type"
            2) "publish"
            3) "id"
            4) "ih98h98w89"
```

## Using Keybase in production

Flask has a built-in web server, but it is not recommended for production usage. It is recommended to put Flask behind a web server which communicates with Flask using WSGI. 

A valid option would be to deploy Keybase together with Nginx as the web server and Gunicorn, which implements the Web Server Gateway Interface. Therefore, it is possible to test Gunicorn as follows. 

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
