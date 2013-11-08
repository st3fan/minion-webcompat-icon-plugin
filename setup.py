# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from setuptools import setup

install_requires = [
    'minion-backend',
    'html5lib==0.99',
    'PIL==1.1.7'
]

setup(name="minion-webcompat-icon-plugin",
      version="0.2",
      description="Icon Plugin for Minion",
      url="https://github.com/mozilla/minion-webcompat-icon-plugin/",
      author="Mozilla",
      author_email="minion@mozilla.com",
      packages=['minion', 'minion.plugins.webcompat'],
      namespace_packages=['minion', 'minion.plugins.webcompat'],
      include_package_data=True,
      install_requires = install_requires)
