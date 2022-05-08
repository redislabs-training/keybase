# keybase

keybase is a Redis based knowledge base. In order to prepare your Python setup, create a virtual environment:

```
python3 -m venv keybasevenv
source keybasevenv/bin/activate
```
Then, install the requirements:

```
pip install -r requirements.txt
```

Configure the Redis database credentials in `REDIS_CFG`. Finally, create the index.

```
FT.CREATE document_idx PREFIX 1 "keybase:kb" SCHEMA name TEXT content TEXT creation NUMERIC SORTABLE update NUMERIC SORTABLE
```

Now you can start the platform:

```
./start.sh
```
