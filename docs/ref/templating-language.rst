Simple Templating Engine
========================

Support generation of any text-based format. A template contains
variables and/or expressions, which get replaced with values when a
template is rendered; and tags, which control the logic of the template.
The template syntax is heavily inspired by Django and Python.

There are a few kinds of delimiters. The default delimiters are
configured as follows:

-  ``{% ... %}`` for Statements
-  ``{{ ... }}`` for Expressions to print to the template output
-  ``{# ... #}`` for Comments not included in the template output

Variables
---------

Template variables are defined by the context dictionary passed to the
template.

You can mess around with the variables in templates provided they are
passed in by the application. Variables may have attributes or elements
on them you can access too like done in standard Python syntax.

Examples:

-  ``{{ foo.bar }}``
-  ``{{ foo['bar'] }}``

If a variable or attribute does not exist, you will get back an error.

Variable names must comply with the same rules as naming variables in
Python: \* The first character of a variable name must be a letter (a-z,
A-Z) or underscore (\_) \* The remaining characters in a variable name
can be letters, numbers or underscore \* Variable names are
case-sensitive

Filters
-------

Variables can be modified by filters. Filters are separated from the
variable by a pipe symbol (``|``) and may have optional arguments are
seperated by colon (``:``). Multiple filters can be chained. The output
of one filter is applied to the next.

For example, ``{{ name|tag1|tag2 }}`` will first call ``tag1`` and
output is passed to ``tag2`` and return is rendered.

Filters that accept arguments have arguments seperated by colon (``:``).
For example: ``{{ listx|join:', ' }}`` will join a list with commas
(``str.join(', ', listx)``).

Supported filters are:

-  ``uppercase``: Convert string to uppercase.
-  ``lowercase``: Convert string to lowercase.
-  ``titlecase``: Convert string to titlecase.
-  ``datetime``: String format datetime.
-  ``base64``: Encode string to base64.

Condition
---------

To add decision-making inside templates, so conditionals are available.
These are just like Python condition but enclosed in ``{%``, ``%}`` like
``{% if <condition> %}``. There must be ``{% endif %}`` block to close
the block.

Example:

::

   {% if user.is_logged_in %}
       <p>Welcome, {{ user.name }}!</p>
   {% endif %}

``if`` block can have optional ``else`` block.

Example:

::

   {% if user.is_logged_in %}
       <p>Welcome, {{ user.name }}!</p>
   {% else %}
       <p>Welcome, guest!</p>
   {% endif %}

Loop
----

To iterate over collection of elements:

Example:

::

   {% for product in product_list %}
       {{ product.name }}: {{ product.price|format_price }}
   {% endfor %}

Comments
--------

To comment-out part of a line in a template, use the comment syntax.

Example:

-  ``{# This is comment and will be ignored #}``
