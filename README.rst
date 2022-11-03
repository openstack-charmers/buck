Buck
====

|snapcraft-badge|

Buck is a tox plugin to provide sane targets (and highly opinionated) to
Charmed OpenStack charms.

Installation
------------

Using the package manager [pip](https://pip.pypa.io/en/stable/) to install buck.

```bash
pip install git+https://github.com/freyes/buck.git#egg=buck
```

Using the snap: ::

    sudo snap install --edge buck


Usage
-----

Tox Plugin
^^^^^^^^^^

Example tox.ini: ::

  [tox]
  skipsdist = True
  skip_missing_interpreters = False
  requires =
    buck @ git+https://github.com/freyes/buck.git@main#egg=buck

Buck Up (experimental)
^^^^^^^^^^^^^^^^^^^^^^

Example charmcraft.yaml: ::

  type: charm
  parts:
    buck:
      plugin: nil
      build-snaps:
        - buck/latest/edge
      override-build: |
        cd /root/parts/charm/
        buck up
    charm:
      after: [buck]
      source: src/
      plugin: reactive
      build-snaps:
        - charm
  bases:
    - build-on:
        - name: ubuntu
          channel: "22.04"
          architectures:
            - amd64
      run-on:
        - name: ubuntu
          channel: "22.04"
          architectures: [amd64, s390x, ppc64el, arm64]

Contributing
------------

Pull requests are welcome. For major changes, please open an issue first to
discuss what you would like to change.

Please make sure to update tests as appropriate.

License
-------

`GPLv3 <./LICENSE>`_


.. |snapcraft-badge| image:: https://github.com/freyes/buck/actions/workflows/snapcraft.yaml/badge.svg
