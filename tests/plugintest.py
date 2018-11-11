TESTEE = 'onkyo-amp'
USER = 'opiopan'

import sys
import importlib
sys.path.append('../personal/' + USER + '/plugin.py/')
sys.path.append('../daemon/')
test = importlib.import_module('onkyo-amp')

c = test.Controller('192.168.22.17')
c.start()
