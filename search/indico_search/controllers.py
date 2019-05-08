# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from flask import jsonify, request
from flask_pluginengine import current_plugin
from sqlalchemy.orm import undefer
from werkzeug.wrappers import Response

from indico.modules.categories import Category
from indico.modules.events import Event
from indico.web.rh import RH

from indico_search.views import WPSearchCategory, WPSearchConference


class RHSearch(RH):
    """Performs a search using the search engine plugin"""

    def _process_args(self):
        if 'confId' in request.view_args:
            self.obj = Event.get_one(request.view_args['confId'], is_deleted=False)
            self.obj_type = 'event'
        elif 'category_id' in request.view_args:
            self.obj = Category.get_one(request.view_args['category_id'], is_deleted=False)
            self.obj_type = 'category' if not self.obj.is_root else None
        else:
            self.obj = Category.get_root()
            self.obj_type = None

    def _process(self):
        with current_plugin.engine_plugin.plugin_context():
            form = current_plugin.search_form(formdata=request.args, prefix='search-', csrf_enabled=False)
            result = None
            if form.validate_on_submit():
                result = current_plugin.perform_search(form.data, self.obj, self.obj_type)
            if isinstance(result, Response):  # probably a redirect or a json response
                return result
            view_class = WPSearchConference if isinstance(self.obj, Event) else WPSearchCategory
            return view_class.render_template('results.html', self.obj, only_public=current_plugin.only_public,
                                              form=form, obj_type=self.obj_type, result=result)


class RHSearchCategoryTitles(RH):
    """Searches for categories with matching titles"""
    def _process(self):
        query = (Category.query
                 .filter(Category.title_matches(request.args['term']),
                         ~Category.is_deleted)
                 .options(undefer('chain_titles'))
                 .order_by(Category.title))
        results = [{
            'title': category.title,
            'path': category.chain_titles[1:-1],
            'url': unicode(category.url)
        } for category in query.limit(7)]
        return jsonify(success=True, results=results, count=query.count())
