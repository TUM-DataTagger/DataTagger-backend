# FDM

A file management tool.

This application uses these core python packages:
* Django 4.2
* Django Rest Framework 3.14
* Django Environ
* pytest

Because of the dependencies, Python 3.9+ is required.

Django 4.2 requires PostgreSQL 12 or higher.

**Note**: See `.env.development` for database credentials.

## Useful dev links

- Frontend: http://localhost:3000/ (using yarn)
- Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/v1/
- Swagger: http://localhost:8000/api/schema/swagger-ui/
- Openapi schema download: http://localhost:8000/api/schema/
- Maildump: http://localhost:1080/
- RabbitMQ Management: http://localhost:15672/  (User: admin, Pass: mypass)

## Installation instructions for development

It is expected you have `docker` as well as `docker compose` set up and running on your machine.

### Local configurations (Override)

Copy the **docker compose.override.example** to **docker compose.override.yml** and add/extend port mappings as needed.

For instance, on a Windows machine you might need to adapt the ports on each service that you want to access from outside to a local ip address:

```
services:
  # Map PostgreSQL Port
  postgresql:
    ports:
      - "127.0.10.20:8400:5432"

  restapi:
    ports:
      - "127.0.10.20:8000:8000"
```

### Setup

To initially build and run the application, do the steps as follows:
* Build the docker images: `docker compose build`
* Run migrations: `docker compose run --rm restapi python manage.py migrate`
* Create superuser: `docker compose run --rm restapi python manage.py createsuperuser`
* Start containers: `docker compose up` or `docker compose start`
* Application should be accessible by browsing [http://localhost:8000/](http://localhost:8000/) (or in case you are on Windows and you did override the docker compose file on [http://127.0.10.20:8000/](http://127.0.10.20:8000/) ).
* On **Windows** you need to use the ip you configured in docker compose for the local port mapping.

The runserver command is directly executed by docker compose when you start the containers.

### Auto-formatter setup
We use isort (https://github.com/pycqa/isort) and black (https://github.com/psf/black) for local auto-formatting and for linting in the CI pipeline.
The pre-commit framework (https://pre-commit.com) provides GIT hooks for these tools, so they are automatically applied before every commit.

Steps to activate:
* Install the pre-commit framework: `pip install pre-commit` (for alternative installation options see https://pre-commit.com/#install)
* Activate the framework (from the root directory of the repository): `pre-commit install`

Hint: You can also run the formatters manually at any time with the following command: `pre-commit run --all-files`

## Installation and update instructions for deployment

You may need the following common tasks during the development of the application:
* Collect static files: `docker compose run --rm restapi python manage.py collectstatic`

## Common Docker Tasks

* Start the containers: ``docker compose up``
* Stop the containers: Either CTRL+C in the commandline, or type ``docker compose stop``
* Stop the containers and delete the run instances: ``docker compose down``
* Stop the containers, delete the run instances and their internal volumes (database and maildump): ``docker compose down -v``

## Manual tasks

* Rebuild images: `docker compose build` (docker compose should replace containers when new images are available)
* Run the test suite: `docker compose run --rm restapi pytest`

#### Migrations

* Create migrations: `docker compose run --rm restapi python manage.py makemigrations`
* Run migrations: `docker compose run --rm restapi python manage.py migrate`
* Undo/Revert migration: `docker compose run --rm restapi python manage.py migrate <app> <number-of-last-migration-file>`

#### Language dependent contents
The app supports different contents for de and en by default.
Extend the LANGUAGES setting in base.py and create a new folder in /app/locale to add a new language package to manage contents for.

* Create translations: `docker compose run --rm restapi python manage.py makemessages`
  (resolve/remove "fuzzy" markers)
* Compile translations: `docker compose run --rm restapi python manage.py compilemessages`

#### Fixtures

* Dump application data to fixture: `docker compose run --rm restapi python manage.py dumpdata auth users --natural-foreign --natural-primary --format json --indent 4 > fixtures/base_contents.json`
* Dump single app data to fixture: `docker compose run --rm restapi python manage.py dumpdata app --natural-foreign --natural-primary --format json > table.json`
* Dump single model data to fixture: `docker compose run --rm restapi python manage.py dumpdata app.model --natural-foreign --natural-primary --format json --indent 4 > table.json`
* Import fixture: `docker compose run --rm restapi python manage.py loaddata fixture.json`

#### Build the documentation

* Build the docs using: `docker compose run --rm restapi make -C ./../docs/ html`
* The documentation should then be available in the [docs/](docs/) folder.

#### Cloning the database volume when changing branches

A common issue are branches with their respective migrations which can render the database unusable after applying migrations and then changing back to a branch without that changes, e.g. removing a non-nullable field in a feature branch but still using it in the master branch.

To avoid this problem you can clone the Docker volume for the current branch and also generate a Docker override file to use it. This ensures that you have different database states for each branch which persist on your local drive until you manually delete them or the Docker override file.

To clone your **default** database volume for your current branch you have to execute the following command from your project root:

```
./helpers/clone_database_volume_for_current_branch.sh -o postgresql
```

The argument `-o` is optional and generates the `docker compose.override.yml` file.

**Important**: Do **NOT** add the `docker compose.override.yml` to the project repository! If you change to a branch where you need another volume clone just execute the command above or delete the override file to use the default volume again.

## Instructions for project

* Only deploy production builds to staging and production servers
* Only deploy the application if all tests pass
* Use the `get_current_request` and `get_current_user` function provided by the **Django UserForeignKey** package.
* Use the `send_mail_via_celery.delay()` function from `fdm.core.tasks` to send mails without blocking requests.

## List of developers

* Anexia <support@anexia-it.com>, Lead developer

## Project related external resources

* [Django documentation](https://docs.djangoproject.com/en/4.2/)
* [Django REST Framework documentation](http://www.django-rest-framework.org/topics/documenting-your-api/)
* [Django Environ documentation](https://django-environ.readthedocs.io/en/latest/)
* [Django UserForeignKey](https://github.com/beachmachine/django-userforeignkey)
* [Django CORS headers](https://github.com/ottoyiu/django-cors-headers)
* [Django debug toolbar documentation](https://django-debug-toolbar.readthedocs.io/en/stable/)
* [Django REST framework JWT Auth](https://github.com/Styria-Digital/django-rest-framework-jwt)
* [GitLab flavored markdown](https://docs.gitlab.com/ee/user/markdown.html)
* [pytest documentation](https://docs.pytest.org/)
