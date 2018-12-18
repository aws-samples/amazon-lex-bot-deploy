=====================
amazon-lex-bot-deploy
=====================


.. image:: https://img.shields.io/pypi/v/lex_bot_deploy.svg
        :target: https://pypi.python.org/pypi/amazon_lex_bot_deploy

.. image:: https://readthedocs.org/projects/lex-bot-deploy/badge/?version=latest
        :target: https://amazon_lex_bot_deploy.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status


Deploy and export Amazon Lex Schema bots easily.
Maintain bots in source, share and use for CI/CD processes::

    lex-bot-deploy --example BookTrip


To get the JSON schema easily::

    lex-bot-get-schema --lex-bot-name BookTrip


And you can specify which schema you would like to deploy obviously::

    lex-bot-deploy -s BookTrip_Export.json

* Free software: MIT-0 license (https://github.com/aws/mit-0)
* Documentation: https://lex-bot-deploy.readthedocs.io.


Features
--------

Let me know :-)

Thoughts:
* make creation of permissions optional
* allow mapping of Lambda endpoints or allow options to map aliases to Lambda function (tbd)


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage