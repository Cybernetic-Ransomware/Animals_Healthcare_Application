## To choose a repository architecture


### Date: 
`2023-06-05`


### Status  
Done


### Context  
We need to choose an approach to building and maintaining the repositories and branches.\
Considered approaches: 
- [x] Monorepo,
- [ ] Polirepo,
---
- [ ] GitFlow,
- [x] GitHub Flow,
- [ ] GitLab Flow,
- [ ] Trunk-based development.


### Decision  
The Monorepo approach will be used due to the small number of developers and the expected number of parallel branches.

The number of developers also affects the decision to manage branches and approach to deployment. 
GitHub-Flow was selected. In a small organization, a least detailed approach will suffice. 


### Consequences  
Possible future migrations will be easier in the direction from simpler to more complicated.


### Keywords
-   GitHub,
-   repository,
-   monorepo,
-   branching.


### Links
*[2023-06-14]*\
[Monorepo vs polyrepo – Taby vs spacje #02](https://youtu.be/7FcbTBtlxqs)

*[2023-06-14]*\
[Git-Flow vs GitHub-Flow](https://quangnguyennd.medium.com/git-flow-vs-github-flow-620c922b2cbd)
