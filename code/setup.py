#!/usr/bin/env python3

import logging

def setup_logger(name=None):
    # create logger
    logger = logging.getLogger(name=name)
    logger.setLevel(logging.INFO)

    # add stream handler (console)
    ch = logging.StreamHandler()

    # create formatter
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s](%(name)s): %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)

    return logger, ch
