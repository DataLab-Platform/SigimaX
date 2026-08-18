Contributing
============

.. meta::
   :description: Contribute to SigimaX project, the open-source GUI framework for scientific applications
   :keywords: SigimaX, contribute, open-source, scientific, GUI, framework, Qt, Python

There are many ways to contribute to SigimaX, depending on how much time you
have, your experience with open source projects, and your skills.

Share your ideas and experiences
--------------------------------

.. only:: html and not latex

   :octicon:`info;1em;sd-text-info` :bdg-success-line:`No coding required`

Besides the classic bug reports and feature requests, you can share your ideas and
experiences for improving SigimaX. In particular, we are very interested in your
feedback on the documentation and tutorials. Moreover, if you have a use case that
you would like to share with the community, please let us know.

.. only:: html and not latex

   .. grid:: 2
       :gutter: 1 2 3 4

       .. grid-item-card:: :octicon:`bug;1em;sd-text-info` Bugs
           :link: https://github.com/DataLab-Platform/SigimaX/issues/new?assignees=&labels=bug&projects=&template=bug_report.md&title=

           Reporting a bug

       .. grid-item-card:: :octicon:`light-bulb;1em;sd-text-info` Enhancements
           :link: https://github.com/DataLab-Platform/SigimaX/issues/new?assignees=&labels=enhancement&projects=&template=feature_request.md&title=

           Suggesting an enhancement

       .. grid-item-card:: :octicon:`book;1em;sd-text-info` Documentation
           :link: https://github.com/DataLab-Platform/SigimaX/issues/new?assignees=&labels=documentation&projects=&template=doc_request.md&title=

           Suggesting a documentation topic

       .. grid-item-card:: :octicon:`mortar-board;1em;sd-text-info` Tutorial
           :link: https://github.com/DataLab-Platform/SigimaX/issues/new?assignees=&labels=documentation&projects=&template=tutorial_request.md&title=

           Suggesting a tutorial topic


.. only:: latex and not html

   Without coding, you can contribute to SigimaX project by:

   - `Reporting a bug <https://github.com/DataLab-Platform/SigimaX/issues/new?assignees=&labels=bug&projects=&template=bug_report.md&title=>`_
   - `Suggesting an enhancement <https://github.com/DataLab-Platform/SigimaX/issues/new?assignees=&labels=enhancement&projects=&template=feature_request.md&title=>`_
   - `Suggesting a documentation topic <https://github.com/DataLab-Platform/SigimaX/issues/new?assignees=&labels=documentation&projects=&template=doc_request.md&title=>`_
   - `Suggesting a tutorial topic <https://github.com/DataLab-Platform/SigimaX/issues/new?assignees=&labels=documentation&projects=&template=tutorial_request.md&title=>`_

Share your scientific/technical knowledge
-----------------------------------------

.. only:: html and not latex

   :octicon:`info;1em;sd-text-info` :bdg-success-line:`No coding required`

Your technical or scientific knowledge is also very valuable to us. You may
contribute documentation or tutorials directly. Or, if you want to write a
tutorial, we will be happy to help you get started.

Without coding, you can contribute to SigimaX project by:

- Writing documentation
- Writing a tutorial
- Sharing a use case of a derived application

Contribute code
---------------

.. only:: html and not latex

   :octicon:`info;1em;sd-text-info` :bdg-info-line:`Coding (beginner)` :bdg-warning-line:`Coding (advanced)`

Even if you are not an experienced developer, you can contribute to the project by:

- Testing new features
- Writing or improving tests
- Reporting and fixing bugs

If you are a developer, you can contribute to the core of the project by fixing
bugs or implementing new features.

Development setup
^^^^^^^^^^^^^^^^^

1. Clone the repository:

   .. code-block:: console

       $ git clone https://github.com/DataLab-Platform/SigimaX.git
       $ cd SigimaX
       $ pip install -e .[dev,doc]

2. Run the tests:

   .. code-block:: console

       $ python scripts/run_with_env.py python -m pytest

3. Format and lint:

   .. code-block:: console

       $ python -m ruff format
       $ python -m ruff check --fix

Code conventions
^^^^^^^^^^^^^^^^

- Use ``from __future__ import annotations`` in all modules
- Define ``__all__`` in all public modules
- Wrap UI strings with ``_()`` for internationalization
- Follow Google-style docstrings
- Use ``snake_case`` for functions, ``PascalCase`` for classes
