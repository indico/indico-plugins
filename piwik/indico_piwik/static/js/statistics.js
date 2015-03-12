$(function() {
    var $t = $T.domain('piwik');
    var treeDOMTarget = '#materialTree';

    /**
     * Clears the DOM element for the graph and then initiates a jqPlot render
     * in the target area.
     *
     * @param source - JSON of dates: {total / unique} hits
     */
    var draw_jqplot_graph = function(source, DOMTarget, replot) {
        $('#' + DOMTarget).html('');

        var plotOptions = {
            axes: {
                xaxis: {
                    renderer: $.jqplot.DateAxisRenderer,
                    min: window.piwikReportDates.start,
                    max: window.piwikReportDates.end
                },
                yaxis: {
                    min: 0,
                    numberTicks: 10
                }
            },
            cursor: {
                show: true,
                zoom: true,
                showTooltip: false
            },
            highlighter: {
                show: true,
                sizeAdjust: 5
            },
            legend: {
                show: true,
                location: 'nw'
            },
            grid: {
                background: '#FFFFFF',
                shadow: false
            },
            series: [{
                showMarker:false,
                lineWidth: 1,
                color: '#CCCCCC',
                label: $t.gettext('Total Hits')
            }, {
                showMarker:false,
                lineWidth: 1,
                color: '#0B63A5',
                label: $t.gettext('Unique Hits')
            }]
        };

        if (replot) {
            $.jqplot(DOMTarget, source, plotOptions).replot();
        } else {
            $.jqplot(DOMTarget, source, plotOptions);
        }
    };

    /**
     * Draw a customized jqTree
     */
    var draw_jqTree = function(treeData) {
        $(treeDOMTarget).tree({
            data: treeData,
            autoOpen: 0,
            saveState: true,
            onCanSelectNode: function(node) {
                // Leaf node (material) can be selected
                return (node.children.length === 0);
            },
            onCreateLi: function(node, $li) {
                if (node.id !== undefined) {
                    $li.find('.title').addClass('selectableNode');
                }
            }
        });
    };

    /**
     * Get base values for API requests
     */
    var get_api_params = function() {
        var params = {'confId': $('#confId').val(),
                      'start_date' : $('#statsFilterStartDate').val(),
                      'end_date' : $('#statsFilterEndDate').val()};

        var contrib_id = $('#contribId').val();
        if (contrib_id != 'None') {
            params.contrib_id = contrib_id;
        }

        return params;
    };

    /**
     * Build URI for page update
     */
    var get_updated_uri = function() {
        var params = {'start_date' : $('#statsFilterStartDate').val(),
                      'end_date' : $('#statsFilterEndDate').val()};
        var contrib_id = $('#updateContribution').val();
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
    var get_jqplot_array_values = function(data, key, with_date) {
        output = [];
        with_date = typeof with_date !== 'undefined' ? with_date : true;

        for (var date in data) {
            hits = data[date];
            value = (with_date) ? [date, hits[key]] : hits[key];
            output.push(value);
        }

        return output;
    };

    /**
     * Load material downloads data via AJAX and draw its graph
     */
    var load_material_graph = function(uri, replot) {
        replot = typeof replot !== 'undefined' ? replot : false;
        var DOMTarget = 'materialDownloadChart';
        var graph_params = get_api_params();
        graph_params.download_url = uri;

        $.ajax({
            url: build_url(PiwikPlugin.urls.data_downloads, graph_params),
            type: 'POST',
            dataType: 'json',
            success: function(data) {
                if (handleAjaxError(data)) {
                    return;
                }
                var materialHits = [get_jqplot_array_values(data.metrics.downloads.individual, 'total'),
                                    get_jqplot_array_values(data.metrics.downloads.individual, 'unique')];
                draw_jqplot_graph(materialHits, DOMTarget, replot);
                $('#materialTotalDownloads').html(data.metrics.downloads.cumulative.total);
            }
        });
    };

    /**
     * Load the material files data and draw its jqTree
     */
    var load_material_tree = function() {
        $(treeDOMTarget).html(progressIndicator(true, true).dom);

        $.ajax({
            url: build_url(PiwikPlugin.urls.material, get_api_params()),
            type: 'POST',
            dataType: 'json',
            success: function(data) {
                if (handleAjaxError(data)) {
                    return;
                }
                if (data.material.tree !== null) {
                    draw_jqTree(data.material.tree);
                } else {
                    $(treeDOMTarget).html($t.gettext('No material found'));
                }
            }
        });
    };

    /**
     * Loads visits data and draw its graph
     */
    var load_visits_graph = function(data) {
        var DOMTarget = 'visitorChart';
        $('#' + DOMTarget).html(progressIndicator(true, true).dom);

        $.ajax({
            url: build_url(PiwikPlugin.urls.data_visits, get_api_params()),
            type: 'POST',
            dataType: 'json',
            success: function(data) {
                if (handleAjaxError(data)) {
                    return;
                }
                var source = [get_jqplot_array_values(data.metrics, 'total'),
                              get_jqplot_array_values(data.metrics, 'unique')];
                draw_jqplot_graph(source, DOMTarget, false);
            }
        });
    };

    /**
     * Load static graphs via ajax
     */
    var load_graphs = function() {
        var graph_requests = [{'endpoint': 'graph_countries', 'report': 'countries'},
                              {'endpoint': 'graph_devices', 'report': 'devices'}];
        $.each(graph_requests, function(index, request) {
            $.ajax({
                url: build_url(PiwikPlugin.urls[request.endpoint], get_api_params()),
                type: 'POST',
                dataType: 'json',
                success: function(data) {
                    if (handleAjaxError(data)) {
                        return;
                    }
                    var graph_holder =  $('#' + request.endpoint);
                    if (data.graphs[request.report] !== null) {
                        graph_holder.attr('src', data.graphs[request.report]);
                    } else {
                        var error = $('<div>').text($t.gettext("No graph data received"));
                        graph_holder.replaceWith(error);
                    }
                }
            });
        });
    };

    var init = function() {
        $('#statsModify').click(function(e) {
            e.preventDefault();
            var $this = $(this);
            var filter = $('#statsFilter');
            if (filter.is(':visible')) {  // hiding it
                $this.text($this.data('msgShow'));
            } else {
                $this.text($this.data('msgHide'));
            }
            filter.slideToggle('fast');
        });

        $('.statsDates').datepicker({
            dateFormat : 'yy-mm-dd',
            defaultDate : $(this).attr('data-default')
        });

        $('#updateQuery').click(function() {
            var url = '?{0}'.format(get_updated_uri());
            window.location.href = url;
        });

        // Event handler for clicking 'selectable' elements from the jqTree.
        $(treeDOMTarget).bind('tree.click', function(event) {
            $('#materialTitle').html(event.node.name);
            $('#materialDownloadChart').html(progressIndicator(true, true).dom);
            load_material_graph(event.node.id, true);
        });

        // jQuery UI Dialog if no data is received via AJAX (timeout)
        $('#dialogNoGraphData').dialog({
            modal: true,
            resizable: false,
            autoOpen: false,
            buttons: {
                Ok: function() {
                    $(this).dialog('close');
                }
            }
        });

        load_graphs();
        load_visits_graph();
        load_material_tree();
    };

    init();
});
