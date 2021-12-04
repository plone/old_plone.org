# ploneorg.core

Policy package to setup a simple volto site.

## Features

### Content types

- Foundation Member

### Initial content

This package contains a simple volto configuration.

Installation
------------

Install ploneorg.core by adding it to your buildout:
```ini
[buildout]

...

eggs =
    ploneorg.core
```

Then running `buildout`

And to create the Plone site:

```shell
./bin/instance run scripts/create_site.py
```

## Contribute

- [Issue Tracker](https://github.com/plone/ploneorg.core/issues)
- [Source Code](https://github.com/plone/ploneorg.core/)

## License

The project is licensed under the GPLv2.
