SLAMon Agent Fleet Manager (AFM)
================================

[![License][license]](http://www.apache.org/licenses/LICENSE-2.0)

[![Requirements Status][req_image]][requirements]
[![Build Status][build]](https://travis-ci.org/SLAMon/slamon-agent-fleet-manager.svg?branch=master)
[![Coverage Status][coverage]](https://coveralls.io/github/SLAMon/slamon-agent-fleet-manager?branch=master)
[![Code Health][health]](https://landscape.io/github/SLAMon/slamon-agent-fleet-manager/master)

$SLAMON_ROOT refers to the directory where the root of this repository lies

# Requirements
* python 3.4
* virtualenv

# Setting up
File slamon_afm/settings.py contains AFM settings in following format:
```
class Settings:
    port = 8080  # Port for the server

    database_name = 'slamon'  # Name of the psql database
    database_user = 'afm'  # Username to use for psql connection
    database_password = 'changeme'  # Password to use for psql connection
```

## Creating postgresql database
```
psql
postgres=# CREATE DATABASE slamon;
postgres=# CREATE DATABASE slamon_tests;
postgres=# CREATE USER afm WITH PASSWORD 'changeme';
postgres=# GRANT ALL PRIVILEGES ON DATABASE slamon TO afm;
postgres=# GRANT ALL PRIVILEGES ON DATABASE slamon_tests TO afm;
\q
```

To create needed tables:
```
cd $SLAMON_ROOT
python ./slamon_afm/admin.py --create-tables
```

To delete tables:
```
cd $SLAMON_ROOT
python ./slamon_afm/admin.py --drop-tables
```

## Creating python virtualenv and installing needed packages
```
cd $SLAMON_ROOT
virtualenv env
. env/bin/active
pip install -r requirements_afm.txt
```

# Running
## Running afm
After entering the virtual environment type in a terminal following:
```
cd $SLAMON_ROOT
export PYTHONPATH=`pwd`
python ./slamon_afm/afm.py
```
### Running tests
In virtual environment:
```
cd $SLAMON_ROOT
nosetests
```
or (if coverage report is also wanted)
```
cd $SLAMON_ROOT
nosetests --with-coverage --cover-package=slamon
```

[license]: https://img.shields.io/:license-Apache%20License%20v2.0-blue.svg
[req_image]: https://requires.io/github/SLAMon/slamon-agent-fleet-manager/requirements.svg?branch=master
[requirements]: https://requires.io/github/SLAMon/slamon-agent-fleet-manager/requirements/?branch=master
[build]: https://travis-ci.org/SLAMon/slamon-agent-fleet-manager.svg?branch=master
[coverage]: https://coveralls.io/repos/SLAMon/slamon-agent-fleet-manager/badge.svg?branch=master&service=github
[health]: https://landscape.io/github/SLAMon/slamon-agent-fleet-manager/master/landscape.svg?style=flat