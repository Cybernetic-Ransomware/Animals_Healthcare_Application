## To set a list of stored data and tables structure


### Date
`2023-07-09`


### Status  
In-building


### Context  
We need to set up a place in documentation to list all collect all data about users and group them by correct place in databases and direct tables.
Main sections of data by sources: 
- user,
- animal,
- medical record note,
- medical document,
- medicines,
- medical facility,
- veterinarian,
- dates sheduling,
- costs counting.


### Decision  
User datatables:
- collected by the registration process:
  - basic provided by user informations:
    - name,
    - email,
    - password,
  - auto-collected:
    - date of registration,
    - default profile image,
    - default background image,
    - default user priviliges (viever, owner, creator, moderator, admin etc.)
- collected after the registration process:
  - provided in profil page:
    - profile image,
    - bacground image choosen,
    - email-change,
    - password-change,
    - date of birthday,
  - stable view(compedium of animals: owned and cared)
  - connections other models:
    - animal - ovner, viewer, 
    - medical record nove - participation in visit
    - medical_place_id,
    - note_
    - 


Medical records (animal timeline)
- animal_id,
- title,
- short_description,
- full_description,
- creation_date,
- modify_date,
- start event date,
- end event date,
- type of events:
  - visit,
  - period of medicine providing,
  - note,
  - measurement,
  - change of feed,
- participants (user, vet),
- place,
- medicals,




### Consequences  
##### _Placeholder_


### Keywords
-   data,
-   database,
-   models.


### Links
