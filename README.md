# Animals Healthcare Application

## <strong> A healthcare data management application for pet owners and carers. </strong>


#### The application provides an extensive notebook that offers:
- A clear timeline filtered by tags and note types.
- Manage your pet's profile, ownership and authorization.
- Share notes between users and animals.
- Registration of biometric measurement data.
- Managing a diet plan with the option of setting reminder notifications via e-mail or Discord.
- Archiving notes from visits to medical facilities.

---
### Functionality:
[ADR](doc/01_adr_functionality.md)

---
### Screenshots
>Click on the image to view full-size

<div align="center">
  <table>
    <tr>
      <td align="center"><p>Animal profile</p><img src="AHC_app/static/media/readme_examples/Animal profile.png" height="250px"></td>
      <td align="center"><p>Full timeline of notes</p><img src="AHC_app/static/media/readme_examples/Full timeline of notes.png" height="250px"></td>
    </tr>
    <tr>
      <td align="center"><p>Diet note details</p><img src="AHC_app/static/media/readme_examples/Diet note details.png" height="250px"></td>
      <td align="center"><p>User registration</p><img src="AHC_app/static/media/readme_examples/User registration.png" height="250px"></td>
    </tr>
  </table>
</div>


---
### Plans for further development:

- Interactive charts for biometric records
- A book of medical facilities and medical personnel
- Databases for medicines and food products
- An SMS gateway, and Messenger chatbots for notifications
- A fixed light-themed frontend, currently blocked in the base.html <html> tag

---
### Requirements:
- Python 3.12.2
- Docker & Docker Compose
- PostgreSQL 15 (instance for volumes)
- Apache CouchDB 3.3.3 (instance for volumes)
- [Packages](AHC_app/Pipfile)
- [pico-1.5.10](https://github.com/picocss/pico/archive/refs/tags/v1.5.10.zip)

---
### Deploy steps:
1. Download repository
2. Set .env file based on template
3. Install Docker Desktop
4. Run containters by "docker-compose up -d --build"

---
### Dev-instance steps:
1. Download repository
2. Set .env file based on template
3. Install Python, Docker Desktop, PostgreSQL and CouchDB as in _Requirements_
4. Install pipenv by "pipenv install"
5. Deploy vevn and synch requirements by "pipenv install --dev"
6. Install precommit hooks by "pre-commit install"
7. Run containters by "docker-compose up -d --build"

---
### Test running:
- by now tests are only reachable by terminal in main container's terminal (container_name: web)
- simply run command "python manage.py test" or use with needed flags

---
### Sources:

* Styles:
  * https://picocss.com/
  * https://uicookies.com/horizontal-timeline/
* Graphics:
  * https://www.flaticon.com/authors/futuer
  * https://www.flaticon.com/authors/pixel-perfect
  * https://www.flaticon.com/authors/riajulislam
  * https://www.midjourney.com/
  * https://pixabay.com/
* Fonts:
  * to link
* Knowledge:
  * https://www.devs-mentoring.pl/


To all the people upper mentioned and not only there,
thank You for your work and positive influence on my motivation!
Keep still doing your best!
