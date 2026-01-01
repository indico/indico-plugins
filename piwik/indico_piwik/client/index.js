// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2026 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import 'jquery';
import './main.css';
import 'indico/jquery/compat/jqplot';

$(function() {
  const $t = $T.domain('piwik');

  /**
   * Clears the DOM element for the graph and then initiates a jqPlot render
   * in the target area.
   *
   * @param source - JSON of dates: {total / unique} hits
   */
  const draw_jqplot_graph = function(source, DOMTarget, replot) {
    $(`#${DOMTarget}`).html('');

    const plotOptions = {
      axes: {
        xaxis: {
          renderer: $.jqplot.DateAxisRenderer,
          min: window.piwikReportDates.start,
          max: window.piwikReportDates.end,
        },
        yaxis: {
          min: 0,
          numberTicks: 10,
        },
      },
      cursor: {
        show: true,
        zoom: true,
        showTooltip: false,
      },
      highlighter: {
        show: true,
        sizeAdjust: 5,
      },
      legend: {
        show: true,
        location: 'nw',
      },
      grid: {
        background: '#FFFFFF',
        shadow: false,
      },
      series: [
        {
          showMarker: false,
          lineWidth: 1,
          color: '#CCCCCC',
          label: $t.gettext('Total Hits'),
        },
        {
          showMarker: false,
          lineWidth: 1,
          color: '#0B63A5',
          label: $t.gettext('Unique Hits'),
        },
      ],
    };

    if (replot) {
      $.jqplot(DOMTarget, source, plotOptions).replot();
    } else {
      $.jqplot(DOMTarget, source, plotOptions);
    }
  };

  /**
   * Get base values for API requests
   */
  const get_api_params = function() {
    const params = {
      event_id: $('#eventId').val(),
      start_date: $('#statsFilterStartDate').val(),
      end_date: $('#statsFilterEndDate').val(),
    };

    const contrib_id = $('#contribId').val();
    if (contrib_id != 'None') {
      params.contrib_id = contrib_id;
    }

    return params;
  };

  /**
   * Build URI for page update
   */
  const get_updated_uri = function() {
    const params = {
      start_date: $('#statsFilterStartDate').val(),
      end_date: $('#statsFilterEndDate').val(),
    };
    const contrib_id = $('#updateContribution').val();
    if (contrib_id != 'None') {
      params.contrib_id = contrib_id;
    }
    return $.param(params);
  };

  /**
   * Extract data from a JSON object returned via the API into
   * the jqPlot array format. If 'with_date' is true
   * each element will be a key-pair value of date-hits.
   */
  const get_jqplot_array_values = function(data, key, with_date) {
    const output = [];
    with_date = typeof with_date !== 'undefined' ? with_date : true;

    for (const date in data) {
      const hits = data[date];
      const value = with_date ? [date, hits[key]] : hits[key];
      output.push(value);
    }

    return output;
  };

  /**
   * Loads visits data and draw its graph
   */
  const load_visits_graph = function(data) {
    const DOMTarget = 'visitorChart';
    $(`#${DOMTarget}`).html(progressIndicator(true, true).dom);

    $.ajax({
      url: build_url(PiwikPlugin.urls.data_visits, get_api_params()),
      type: 'POST',
      dataType: 'json',
      success(data) {
        if (handleAjaxError(data)) {
          return;
        }
        const source = [
          get_jqplot_array_values(data.metrics, 'total'),
          get_jqplot_array_values(data.metrics, 'unique'),
        ];
        draw_jqplot_graph(source, DOMTarget, false);
      },
    });
  };

  /**
   * Load static graphs via ajax
   */
  const load_graphs = function() {
    const graph_requests = [
      {endpoint: 'graph_countries', report: 'countries'},
      {endpoint: 'graph_devices', report: 'devices'},
    ];
    $.each(graph_requests, function(index, request) {
      $.ajax({
        url: build_url(PiwikPlugin.urls[request.endpoint], get_api_params()),
        type: 'POST',
        dataType: 'json',
        success(data) {
          if (handleAjaxError(data)) {
            return;
          }
          const graph_holder = $(`#${request.endpoint}`);
          if (data.graphs[request.report] !== null) {
            graph_holder.attr('src', data.graphs[request.report]);
          } else {
            const error = $('<div>').text($t.gettext('No graph data received'));
            graph_holder.replaceWith(error);
          }
        },
      });
    });
  };

  const init = function() {
    $('#statsModify').click(function(e) {
      e.preventDefault();
      const $this = $(this);
      const filter = $('#statsFilter');
      if (filter.is(':visible')) {
        // hiding it
        $this.text($this.data('msgShow'));
      } else {
        $this.text($this.data('msgHide'));
      }
      filter.slideToggle('fast');
    });

    $('.statsDates').datepicker({
      dateFormat: 'yy-mm-dd',
      defaultDate: $(this).attr('data-default'),
    });

    $('#updateQuery').click(function() {
      const url = '?{0}'.format(get_updated_uri());
      window.location.href = url;
    });

    // jQuery UI Dialog if no data is received via AJAX (timeout)
    $('#dialogNoGraphData').dialog({
      modal: true,
      resizable: false,
      autoOpen: false,
      buttons: {
        Ok() {
          $(this).dialog('close');
        },
      },
    });

    load_graphs();
    load_visits_graph();
  };

  init();
});
