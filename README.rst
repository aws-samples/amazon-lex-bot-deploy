=====================
amazon-lex-bot-deploy
=====================


.. image:: https://img.shields.io/pypi/v/lex_bot_deploy.svg
        :target: https://pypi.python.org/pypi/amazon_lex_bot_deploy

.. image:: https://readthedocs.org/projects/lex-bot-deploy/badge/?version=latest
        :target: https://amazon_lex_bot_deploy.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status


Amazon Lex Bot Deploy
---------------------

The sample code provides a deploy function and an executable to easily deploy an Amazon Lex bot based on a Lex Schema file.

License Summary
---------------

This sample code is made available under a modified MIT license. See the LICENSE file.


Deploy and export Amazon Lex Schema bots easily.
Maintain bots in source, share and use for CI/CD processes::

    pip install amazon-lex-bot-deploy

then::


    lex-bot-deploy --example BookTrip


To get the JSON schema easily::

    lex-bot-get-schema --lex-bot-name BookTrip


And you can specify which schema you would like to deploy obviously::

    lex-bot-deploy -s BookTrip_Export.json

For an example how to use the API check the CLI command https://github.com/aws-samples/amazon-lex-bot-deploy/blob/master/bin/lex-bot-deploy

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
