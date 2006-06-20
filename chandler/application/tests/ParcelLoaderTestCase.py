#   Copyright (c) 2003-2006 Open Source Applications Foundation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


"""
A helper class which sets up and tears down a repository and anything else
that a parcel loader unit test might need
"""

import unittest, os, sys

import repository.tests.RepositoryTestCase as RepositoryTestCase

import application

# Fix for hardhat running test cases with sys.path including a subpackage :(
mydir = os.path.dirname(__file__)
if mydir in sys.path:
    sys.path.remove(mydir)


class ParcelLoaderTestCase(RepositoryTestCase.RepositoryTestCase):

    def setUp(self):

        super(ParcelLoaderTestCase, self)._setup(self)

        self.testdir = os.path.join(self.rootdir, 'application', 'tests')

        super(ParcelLoaderTestCase, self)._openRepository(self)
