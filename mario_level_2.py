#!/usr/bin/env python

"""
This is the main file to run Level 2 of Super Mario Bros.
""" 

import sys
import pygame as pg
from data.main_level_2 import main
import cProfile

if __name__=='__main__':
    main()
    pg.quit()
    sys.exit()