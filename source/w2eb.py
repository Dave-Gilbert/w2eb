#!/usr/bin/python

import sys

from w2ebStartup import Startup
from w2ebMain import Main


if __name__ == '__main__':

    opts = Startup()
    err, foot_dict_list, sect_label_href_list = Main(opts)
    if err:
        sys.exit(1)

