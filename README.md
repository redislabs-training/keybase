# <img src="src/static/images/keybase.png" height="50px">

keybase is a Redis based knowledge base. In order to prepare your Python setup, create a virtual environment:

```
python3 -m venv keybasevenv
source keybasevenv/bin/activate
python3 -m pip install --upgrade pip
```
Then, install the requirements:

```
pip3 install -r requirements.txt
```

Configure the Redis database credentials in `config.py`. Finally, create the index.

```
FT.CREATE document_idx PREFIX 1 "keybase:kb" SCHEMA name TEXT content TEXT creation NUMERIC SORTABLE update NUMERIC SORTABLE
```

Now you can start the platform:

```
./start.sh
```
