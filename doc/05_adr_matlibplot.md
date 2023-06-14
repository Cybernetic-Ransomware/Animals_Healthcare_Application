## To create a technology to chart visualisations of data


### Date: 
`2023-06-05`


### Status  
Proposed


### Context  
We need to choose a technology to create charts for the application.\
Considered approaches: 
- Static charts:
	- Matplotlib,


- Interactive dashboards:
	- Dash-Plotly microservice,
    - Chart.js,


### Decision  
To avoid the proliferation of microservices, a decision has been made to prototype using a static method of generating charts. 
The presented data is not expected to require frequent refreshing and filtering of the range.


### Consequences  
A faster development process and the possibility of future functionality replacement.
After preparing the static prototype, tests with Chart.js will be carried out and the cost of implementation will be estimated.


### Keywords
-   Matplotlib,
-   Dash Plotly,
-   Dashboards,
-   Charts,
-   Data visualisation.


### Links
*[2023-06-14]*\
Homepages:

	https://matplotlib.org/

    https://dash.plotly.com/

	https://www.chartjs.org/
