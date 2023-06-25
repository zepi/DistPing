$(document).ready(function () {
    $('.navbar-burger').each(function () {
        $(this).click(function () {
            var target = $('#' + $(this).data('target'));
            
            $(this).toggleClass('is-active');
            target.toggleClass('is-active');
        });
    });
});

var ws = null;

function distPingInitializeWebsocket(scheme, host, callback)
{
    var dsn = scheme + '://' + host + '/ws';

    if (window.WebSocket) {
        ws = new WebSocket(dsn);
    } else if (window.MozWebSocket) {
        ws = MozWebSocket(dsn);
    } else {
        console.log('WebSocket not supported');
        return;
    }

    ws.onmessage = function (evt) {
        var jsonMsg = JSON.parse(evt.data);

        if (jsonMsg == false) {
            return;
        }

        callback(jsonMsg);
    };

    ws.onopen = function() {
        ws.send(JSON.stringify({command: 'get_status'}));
        console.log('DistPing WebSocket connected');
    };

    ws.onclose = function(evt) {
        setTimeout(function () {
            distPingInitializeWebsocket(scheme, host, callback);
        }, 5000);
    };
}

function updateStatus(message)
{
    let el = $('.target[data-path="' + message.path + '"]');
    let cardStatus = el.find('.card-status-start');
    let icon = el.find('.target-title .ti');

    el.removeClass('target-online target-unstable target-offline target-unknown');
    cardStatus.removeClass('bg-secondary bg-success bg-warning bg-danger');
    icon.removeClass('ti-help-octagon text-secondary ti-circle-check text-success ti-alert-circle text-warning ti-cross-circle text-danger');
    if (message.status === 'online') {
        el.addClass('target-online');
        cardStatus.addClass('bg-success');
        icon.addClass('ti-circle-check text-success');
    } else if (message.status === 'unstable') {
        el.addClass('target-unstable');
        cardStatus.addClass('bg-warning');
        icon.addClass('ti-alert-circle text-warning');
    } else if (message.status === 'offline') {
        el.addClass('target-offline');
        cardStatus.addClass('bg-danger');
        icon.addClass('ti-circle-x text-danger');
    } else {
        el.addClass('target-unknown');
        cardStatus.addClass('bg-secondary');
        icon.addClass('ti-help-octagon text-secondary');
    }

    let chartTime = null
    if (el.find('.ping-avg-value').length) {
        if (message.data.avg > 0) {
            el.find('.ping-min-value').text(message.data.min + ' ms');
            el.find('.ping-avg-value').text(message.data.avg + ' ms');
            el.find('.ping-max-value').text(message.data.max + ' ms');
            el.find('.ping-loss-value').text(message.data.loss + '%');

            el.find('.ping-loss-value').removeClass('text-danger text-warning status-important');
            if (message.data.loss == 100) {
                el.find('.ping-loss-value').addClass('text-danger status-important');
            } else if (message.data.loss > 0) {
                el.find('.ping-loss-value').addClass('text-warning status-important');
            }

            chartTime = message.data.avg;
        } else {
            el.find('.ping-min-value').text('n/a');
            el.find('.ping-avg-value').text('n/a');
            el.find('.ping-max-value').text('n/a');
            el.find('.ping-loss-value').text('n/a').removeClass('text-danger text-warning status-important');
        }
    }

    if (el.find('.request-time-value').length) {
        if (message.data.time > 0) {
            el.find('.request-time-value').text(message.data.time + ' ms');

            chartTime = message.data.time;
        } else {
            el.find('.request-time-value').text('n/a');
        }
    }

    let chart = el.find('.target-chart').data('chart');
    if (chart) {
        chart.updateOptions({
            xaxis: {
                min: Date.now() - (5 * 60 * 1000)
            }
        });
        chart.appendData([{
            data: [[Date.now(), parseFloat(chartTime)]]
        }]);
    }

    updateSummaryCounter();
}

function updateObserverCount(message)
{
    $('.counter-observers').text(message.numberOfConnectedObservers + ' / ' + message.numberOfTotalObservers);
}

function updateSummaryCounter()
{
    $('.counter-targets-online').text($('.target.target-online').length);
    $('.counter-targets-unstable').text($('.target.target-unstable').length);
    $('.counter-targets-offline').text($('.target.target-offline').length);
}