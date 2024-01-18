## To choose a project architecture


### Date: 
`2023-06-05`


### Status  
Done


### Context  
We need to choose an approach to building the project's application structure.\
Considered approaches: 
- [x] Monolith,
- [ ] Microservices.


### Decision  
Due to the selection of Django as the main framework, an application in the monolithic architecture will be created, 
open via APIs to the possibility of adding selective functionalities in the form of microservices.


### Consequences  
Each new functionality will need to be considered to determine it will be easier to implement as a fragment of the monolith or as a new microservice.


### Keywords
-   Main architecture,
-   Monolith,
-   Microservices.


### Links
	pass
