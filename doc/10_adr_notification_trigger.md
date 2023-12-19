## To set a tech-stack for notifications


### Date
`2023-12-19`


### Status  
In-building


### Context  
We need to choose a technology for sending set by users notifications.
The basic channel for sending notifications include:
- e-mail,
- sms,
- chatbot (Discord or Messenger).

Main risks: overwhelming a database by frequent requests.
It is important to use intervals and delays to queue the broker.

Options:
- Celery Beat,
- django-crontab,
- django-cron.


### Decision  
Django-crontab


### Consequences  

1. **Integration with Django:** django-crontab is a Django extension, making it a natural choice for seamlessly scheduling tasks in a Django-based application. This integration facilitates code maintenance and management.

2. **Ease of Use:** django-crontab is easy to configure and use. Leveraging the same mechanisms as Django, it imposes minimal overhead on the development.

3. **Precise Task Scheduling:** django-crontab allows for precise task scheduling, crucial for handling notifications. Specific 1h time intervals on parametrized minute and easy to count delays can be configured, enabling effective broker queuing and minimizing the risk of database overload.

4. **Flexibility:** django-crontab offers flexibility in configuring cron tasks. This enables tailoring settings to the specific requirements of the project and adapting to potential future changes.


### Keywords
-   Celery,
-   Cronjobs,
-   queue, 
-   broker,
-   subscriptions,.


### Links
