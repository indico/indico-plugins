# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
from functools import wraps

from flask import current_app


def parallelize(func, entries, batch_size=200):
    @wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=batch_size)
        tasks = []
        for entry in entries:
            def run(app, *_args, **_kwargs):
                with app.app_context():
                    return func(*_args, **_kwargs)
            tasks.append(loop.run_in_executor(
                executor, run, current_app._get_current_object(), entry, *args, **kwargs
            ))
            if len(tasks) >= batch_size:
                loop.run_until_complete(asyncio.gather(*tasks))
                del tasks[:]
        if tasks:
            loop.run_until_complete(asyncio.gather(*tasks))

    return wrapper
