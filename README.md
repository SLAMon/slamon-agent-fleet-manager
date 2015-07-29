SLAMon Agent Fleet Manager (AFM)
================================

[![License][license]](http://www.apache.org/licenses/LICENSE-2.0)

[![Latest PyPI Version](https://badge.fury.io/py/slamon-afm.svg)](http://badge.fury.io/py/slamon-afm)
[![Supported Python Versions](https://img.shields.io/pypi/pyversions/slamon-afm.svg)](pypi)
[![Requirements Status][requirements_image]][requirements]

[![Build Status][build]](https://travis-ci.org/SLAMon/slamon-agent-fleet-manager.svg?branch=master)
[![Coverage Status][coverage]](https://coveralls.io/github/SLAMon/slamon-agent-fleet-manager?branch=master)
[![Code Health][health]](https://landscape.io/github/SLAMon/slamon-agent-fleet-manager/master)


# Requirements
* python 3.3+

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
slamon-afm create-tables
```

To delete tables:
```
slamon-afm drop-tables
```

## Creating python virtualenv and installing Agent Fleet Manager
```
pip install slamon-afm
```

# Running
## Running afm
Running an instance of AFM from commandline
```
slamon-afm run HOST_NAME
```
For example running AFM on localhost
```
slamon-afm run localhost
```

### Running tests
$SLAMON_ROOT refers to the repository root.
```
cd $SLAMON_ROOT
pip install -r test_requirements.txt
nosetests
```
or (if coverage report is also wanted)
```
cd $SLAMON_ROOT
pip install -r test_requirements.txt
nosetests --with-coverage --cover-package=slamon_afm
```

[license]: https://img.shields.io/:license-Apache%20License%20v2.0-blue.svg
[requirements_image]: https://requires.io/github/SLAMon/slamon-agent-fleet-manager/requirements.svg?branch=master
[requirements]: https://requires.io/github/SLAMon/slamon-agent-fleet-manager/requirements/?branch=master
[build]: https://travis-ci.org/SLAMon/slamon-agent-fleet-manager.svg?branch=master
[coverage]: https://coveralls.io/repos/SLAMon/slamon-agent-fleet-manager/badge.svg?branch=master&service=github
[health]: https://landscape.io/github/SLAMon/slamon-agent-fleet-manager/master/landscape.svg?style=flat
[latest_version]: https://badge.fury.io/py/slamon-afm.svg
[pypi]: https://pypi.python.org/pypi/slamon-afm/


