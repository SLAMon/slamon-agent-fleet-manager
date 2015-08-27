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
* qlalchemy>=1.0.6,
* jsonschema>=2.5.1
* python_dateutil>= 2.4.2
* flask>=0.10
* flask-sqlalchemy>=2.0

# Installation

Easiest way to install SLAMon Agent Fleet Manager is using pip, this will also take care of the dependencies:

```
pip install slamon-afm
```

# Configuration

By default, SLAMon AFM will try to lookup configuration file location in the *SLAMON_AFM_CFG* environment variable.
Alternatively, you can specify the configuration file path or override the database URI on command line:

```
  --database-uri DATABASE_URI
                        Set the AFM database URI, defaults to in memory sqlite
  --config CONFIG, -c CONFIG
                        Load AFM configuration from a file
```

## Configuration keys

SLAMon AFM usess the configuration utilities provided by Flask. In addition to SLAMon AFM specific configuration keys,
you can tune the generic [Flask](http://flask.pocoo.org/docs/0.10/config/#builtin-configuration-values) and
[Flask-SQLAlchemy](https://pythonhosted.org/Flask-SQLAlchemy/config.html#configuration-keys) configuration keys using
the same configuration file. 

Key                       | Description
--------------------------|----------------------------
SQLALCHEMY_DATABASE_URI   | The database URI that should be used for the connection. default='sqlite://'
AGENT_RETURN_TIME         | Default polling interval for agents, defined in seconds. default=60
AGENT_ACTIVE_THRESHOLD    | Timeout to wait before considering an agent as lost, defined in seconds. default=300
AUTO_CREATE               | Automatically create database tables before the first request. default=True

## Creating a PostgreSQL database for AFM

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
slamon-afm --database-uri="postgresql+psycopg2://user:pass@host/db" create-tables
```

To delete tables:

```
slamon-afm --database-uri="postgresql+psycopg2://user:pass@host/db" drop-tables
```

# Running

Running an instance of AFM from commandline

```
usage: slamon-afm run [-h] host port

Run an instance of an Agent Fleet Manager that listens to given host address

positional arguments:
  host        Host name or address e.g. localhost or 127.0.0.1
  port        Listening port, defaults to 8080
```

For example running AFM listening for all interfaces on port 8080:

```
slamon-afm run 0.0.0.0 8080
```

# Running the tests

Running the tests with nose:

```
pip install -r test_requirements.txt
nosetests
```

or with coverage report:

```
nosetests --with-coverage --cover-package=slamon_afm
```

# Things to do

* Separate application logic from routes into smaller functions
    * proper unittests for these
* Mock database usage in tests
* Extend the BPMS API with task TTL support


[license]: https://img.shields.io/:license-Apache%20License%20v2.0-blue.svg
[requirements_image]: https://requires.io/github/SLAMon/slamon-agent-fleet-manager/requirements.svg?branch=master
[requirements]: https://requires.io/github/SLAMon/slamon-agent-fleet-manager/requirements/?branch=master
[build]: https://travis-ci.org/SLAMon/slamon-agent-fleet-manager.svg?branch=master
[coverage]: https://coveralls.io/repos/SLAMon/slamon-agent-fleet-manager/badge.svg?branch=master&service=github
[health]: https://landscape.io/github/SLAMon/slamon-agent-fleet-manager/master/landscape.svg?style=flat
[latest_version]: https://badge.fury.io/py/slamon-afm.svg
[pypi]: https://pypi.python.org/pypi/slamon-afm/


