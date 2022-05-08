# keybase

Redis based knowledge base


```
FT.CREATE document_idx PREFIX 1 "reknown:kb" SCHEMA name TEXT content TEXT creation NUMERIC SORTABLE update NUMERIC SORTABLE
```

Check it with:

```
FT._LIST
```

And search using:

```
FT.SEARCH document_idx "@name:stack*" RETURN 1 name SORTBY name
```
