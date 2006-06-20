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


# prints the item that's currently selected.

import osaf.framework.blocks.Block as Block
from osaf import webserver
import webbrowser

f = Block.Block.getFocusBlock()

for server in webserver.Server.iterItems(f.itsView):
    if not server.isActivated():
        server.startup()

try:
    i = list(f.widget.SelectedItems())[0]
except AttributeError:
    i = None


if i is not None:
    #XXX [i18n] i.itsPath should be an ascii string however
    #    it is a repository.util.Path.Path.
    #    In addition when doing an str() or i.itsPath
    #    in certain cases the value returned is unicode.
    #    This is not correct and needs to be fixed.
    #    This hack handles the case where the path is returned as
    #    unicode.

    path = unicode(i.itsPath)[1:]

    url = 'http://localhost:1888/repo%s' % path.encode('utf8')
    webbrowser.open(url)
