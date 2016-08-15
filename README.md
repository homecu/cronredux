cronredux
========
A revisit of cron service using more modern interaction patterns.


About
--------
* Command line friendly
* Does not use mail protocols
* Does not use syslog
* Slack notifications
* Concurrency control
  * You can schedule the number of jobs to run concurrently
  * Overlap of tasks can be enabled or disabled depending on your use cases.


Requirements
--------
* `asyncio` Python Library
* `shellish` Python Library
* `crontab` Python Library


Installation
--------
    python3 ./setup.py build
    python3 ./setup.py install


Compatibility
--------
* Python 3.4+


TODO
--------
Web server for `/health` endpoint and status info.
