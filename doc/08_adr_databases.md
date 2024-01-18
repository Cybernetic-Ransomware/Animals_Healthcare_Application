## To choose DBMS


### Date: 
`2023-06-05`


### Status  
In-building


### Context  
We need to choose a database for a specific task within the application.\
Considered DBMS: 
- [x] PostgreSQL,
- [ ] MS SQL,
- [ ] MySQL,
- [ ] SQLite,
- [ ] MongoDB,
- [x] Redis    --to integrate,
- [ ] Firebird,
- [x] CouchDB.


### Decision  
Tree databases have been selected for routing testing.

PostgreSQL - quick database creation and configuration with a good SQL interface. It has many use cases with Django.

CouchDB - native support for files as attachments. Non-relational database, intended for file storage only.

Redis - default broker for Celery queue.


### Consequences  
In basic form database routing is required. 
The implementation should be quick, as the second database will be used only for storing attachment files.


### Keywords
-   DBMS,
-   database.


### Links
*[2023-06-14]*\
Homepages:

	https://www.postgresql.org/

    https://www.mysql.com/

    https://www.sqlite.org/index.html

    https://www.mongodb.com/
    
    https://redis.io/
    
    https://firebirdsql.org/
    
    https://couchdb.apache.org/

*[2023-01-24]*\
[How to use PostgreSQL with Django](https://www.enterprisedb.com/postgres-tutorials/how-use-postgresql-django)

*[2008-08-18]*\
[An Introduction to Using CouchDB with Django](https://lethain.com/an-introduction-to-using-couchdb-with-django/)
