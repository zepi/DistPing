var overviewChartTime = 900;
var maxNumberOfDataPoints = overviewChartTime / 30; // view duration divided by ping interval 

var targets = {};
var charts = {};
var chartBasicConfig = {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: "Min.",
            borderColor: 'rgba(0, 200, 0, 0.25)',
            backgroundColor: 'rgba(0, 200, 0, 0.25)',
            pointRadius: 0,
            pointHitRadius: 6,
            borderWidth: 0.1,
            fill: '+1',
            data: [],
        }, {
            label: "Avg.",
            borderColor: '#000000',
            pointRadius: 0,
            pointHitRadius: 6,
            borderWidth: 2,
            hitRadius: 2,
            fill: false,
            data: [],
        }, {
            label: "Max.",
            borderColor: 'rgba(200, 0, 0, 0.25)',
            backgroundColor: 'rgba(200, 0, 0, 0.25)',
            pointRadius: 0,
            pointHitRadius: 6,
            borderWidth: 0.1,
            fill: '-1',
            data: [],
        }, {
            label: 'Loss',
            backgroundColor: '#d30101',
            borderColor: '#d30101',
            pointRadius: 0,
            pointHitRadius: 6,
            borderWidth: 1,
            fill: false,
            yAxisID: 'packets-axis',
            data: []
        }]
    },
    options: {
        animation: {
            duration: 0,
        },
        hover: {
            animationDuration: 0,
        },
        responsive: true,
        responsiveAnimationDuration: 0,
        title:{
            text: "Chart"
        },
        layout: {
            padding: {
                top: 20,
                left: 10,
                right: 10,
                bottom: 10
            }
        },
        legend: {
            display: false
        },
        scales: {
            xAxes: [{
                type: "time",
                ticks: {
                    maxRotation: 0,
                    callback: function (label, index, labels) {
                        if (labels[index] == undefined) {
                            return null;
                        }
                        
                        var date = moment(labels[index].value);

                        if (date.minutes() % 2 == 0) {
                            return date.format('HH:mm');
                        }
                        
                        return null;
                    }
                },
                time: {
                    displayFormats: {
                        second: 'HH:mm',
                        minute: 'HH:mm',
                        hour: 'HH:mm'
                    },
                    unit: 'minute',
                },
                scaleLabel: {
                    display: false,
                    labelString: 'Date'
                },
            }, ],
            yAxes: [{
                type: 'linear',
                offset: true,
                scaleLabel: {
                    display: true,
                    labelString: 'ms',
                    fontColor: '#000000'
                },
                ticks: {
                    beginAtZero: true,
                    fontColor: '#000000',
                    min: 0,
                }
            }, {
                offset: true,
                position: 'right',
                id: 'packets-axis',
                scaleLabel: {
                    display: true,
                    labelString: 'loss',
                    fontColor: '#d30101'
                },
                gridLines: {
                    display: false,
                },
                ticks: {
                    min: 0,
                    max: 100,
                    fontColor: '#d30101'
                }
            }]
        },
        elements: {
            line: {
                tension: 0,
            }
        },
        tooltips: {
            enabled: false,
            mode: 'index',
            custom: function (tooltip) {
                if (tooltip.opacity == 0) {
                    updateCardData(getCardForChart(this._chart), false);
                }
                
                if (!tooltip.dataPoints) {
                    return;
                }

                values = {
                    time: tooltip.title[0] / 1000,
                    min: tooltip.dataPoints[0].yLabel,
                    avg: tooltip.dataPoints[1].yLabel,
                    max: tooltip.dataPoints[2].yLabel,
                    loss: tooltip.dataPoints[3].yLabel,
                };
                
                updateCardData(getCardForChart(this._chart), values);
            }
        },
    }
};

$(document).ready(function () {
    $('.navbar-burger').each(function () {
        $(this).click(function () {
            var target = $('#' + $(this).data('target'));
            
            $(this).toggleClass('is-active');
            target.toggleClass('is-active');
        });
    });
    
    $('body').on('click', '.target-link', function () {
        console.log($(this).data('host'));
    });
    
    loadTargets();
});

function loadTargets()
{
    $.post('/data/get_targets/', { }, function (responseData) {
        targets = responseData;
        
        for (var key in responseData) {
            var group = responseData[key];
            
            var groupContainer = $('<div></div>').addClass('target-group').appendTo('#overview-page .targets-list');
            var title = $('<h3></h3>').addClass('title').text(group.name).appendTo(groupContainer);
            var container = $('<div></div>').addClass('targets-container columns is-multiline').appendTo(groupContainer);
            
            for (var targetKey in group.targets) {
                target = group.targets[targetKey];
                
                addTargetsPanelElement(target);
                addTargetCard(target, container);
            }            
        }
        
        loadLatestHistory();
    }, 'json');
}

function loadLatestHistory()
{
    $.post('/data/get_latest_history/', { duration: overviewChartTime }, function (responseData) {
        for (var key in responseData) {
            card = $('#overview-page .targets-list').find('div.card[data-host="' + key + '"]');
            

            if (card.length == 0) {
                continue;
            }

            targetData = responseData[key];
            chart = charts[key];

            for (var number in targetData) {
                var posData = targetData[number];

                chart.data.labels.push(posData.time * 1000);
                chart.data.datasets[0].data.push(posData.min);
                chart.data.datasets[1].data.push(posData.avg);
                chart.data.datasets[2].data.push(posData.max);
                chart.data.datasets[3].data.push(posData.loss);
            }
            
            if (posData != undefined) {
                card.data('last-update', posData.time);
            }
            
            recalculateMaxValue(chart, chart.data.datasets[2].data);
            
            chart.update();
            updateCardData(card, posData, true);
        }

        refreshStatistics();
        setInterval("refreshStatistics()", 10000);
    }, 'json');
}

function refreshStatistics()
{
    var counterOnline = 0;
    var counterUnstable = 0;
    var counterOffline = 0;
    $.post('/data/get_latest_values/', { }, function (responseData) {
        for (var key in responseData) {
            target = responseData[key];
            
            if (target.status == 'online') {
                counterOnline++;
            } else if (target.status == 'unstable') {
                counterUnstable++;
            } else if (target.status == 'offline') {
                counterOffline++;
            }
            
            updateTargetData(key, target);
        }
        
        $('.counter-targets-online').text(counterOnline);
        $('.counter-targets-unstable').text(counterUnstable);
        $('.counter-targets-offline').text(counterOffline);
    }, 'json');
    
    $.post('/data/get_observer_connections/', { }, function (responseData) {
        $('#overview-page .counter-observers').text(responseData.connected + '/' + responseData.total); 
    }, 'json');
}

function addTargetsPanelElement(element)
{
    if ($('.targets-panel').find('a[data-host="' + element.host + '"]').length > 0) {
        return;
    }
    
    var panelElement = $('<a></a>').addClass('panel-block').addClass('target-link').attr('data-host', element.host);
    
    var panelIconSpan = $('<span></span>').addClass('panel-icon');
    panelElement.append(panelIconSpan);
    
    var panelIcon = $('<i></i>').addClass('fa').addClass('fa-dot-circle-o');
    panelIconSpan.append(panelIcon);
    
    panelElement.append(element.name);
    
    $('.targets-panel').append(panelElement);
}

function addTargetCard(element, container)
{
    if (container.find('div.card[data-host="' + element.host + '"]').length > 0) {
        return;
    }
    
    // Add the card
    var column = $('<div></div>').addClass('column is-one-third').appendTo(container);
    var cardElement = $('<div></div>').addClass('card').attr('data-host', element.host).appendTo(column);
    
    // Add the chart area
    var chartArea = $('<div></div>').addClass('card-image').appendTo(cardElement);
    var chartFigure = $('<figure></figure>').addClass('image').appendTo(chartArea);
    var chartElement = $('<canvas></canvas>').attr('id', 'chart-' + element.host).addClass('chart chart-area').appendTo(chartFigure);
    
    // Add the card content
    var cardContent = $('<div></div>').addClass('card-content').appendTo(cardElement);
    
    // Add the icon and titles
    var mediaContainer = $('<div></div>').addClass('media').appendTo(cardContent);
    var mediaLeftIconContainer = $('<div></div>').addClass('media-left').appendTo(mediaContainer);
    var mediaLeftIconFigure = $('<figure></figure>').addClass('card-icon image is-48x48').appendTo(mediaLeftIconContainer);
    var mediaLeftIcon = $('<i></i>').addClass('fa fa-check-circle has-text-success').appendTo(mediaLeftIconFigure);
    
    var titleContainer = $('<div></div>').addClass('media-content').appendTo(mediaContainer);
    var title = $('<div></div>').addClass('title is-4').text(element.name).appendTo(titleContainer);
    var subtitle = $('<div></div>').addClass('subtitle is-6').text(element.host).appendTo(titleContainer);
    
    var moreButton = $('<a></a>').attr('href', '#').addClass('button is-pulled-right is-overlay is-medium target-link').data('host', element.host).appendTo(mediaContainer);
    var moreButtonIcon = $('<i></i>').addClass('fa fa-info').appendTo(moreButton);
    
    // Add the important numbers
    var statusTitle = $('<div></div>').addClass('title is-6 title-status-table').text('Status').appendTo(cardContent);
    var statusTable = $('<table></table>').addClass('table is-bordered is-fullwidth is-narrow is-marginless').appendTo(cardContent);
    var statusTableHead = $('<thead></thead>').appendTo(statusTable);
    var statusTableHeadRow = $('<tr></tr>').appendTo(statusTableHead);
    
    $('<th></th>').width('25%').addClass('has-text-centered').text('Loss').appendTo(statusTableHeadRow);
    $('<th></th>').width('25%').addClass('has-text-centered').text('Min').appendTo(statusTableHeadRow);
    $('<th></th>').width('25%').addClass('has-text-centered').text('Avg').appendTo(statusTableHeadRow);
    $('<th></th>').width('25%').addClass('has-text-centered').text('Max').appendTo(statusTableHeadRow);
    
    var statusTableBody = $('<thead></thead>').appendTo(statusTable);
    var statusTableBodyRow = $('<tr></tr>').appendTo(statusTableBody);
    
    $('<td></td>').addClass('has-text-centered status-data-loss').text('-').appendTo(statusTableBodyRow);
    $('<td></td>').addClass('has-text-centered status-data-min').text('-').appendTo(statusTableBodyRow);
    $('<td></td>').addClass('has-text-centered status-data-avg').text('-').appendTo(statusTableBodyRow);
    $('<td></td>').addClass('has-text-centered status-data-max').text('-').appendTo(statusTableBodyRow);
    
    // Build chart
    config = jQuery.extend(true, {}, chartBasicConfig);
    
    charts[element.host] = new Chart(chartElement[0].getContext('2d'), config);
}

function updateTargetData(host, targetData)
{
    var card = $('#overview-page .targets-list').find('div.card[data-host="' + host + '"]');
    if (card.length == 0 || card.data('last-update') == targetData.time) {
        return;
    }

    updateCardData(card, targetData, true);
    
    chart = charts[host];
    
    chart.data.labels.push(targetData.time * 1000);
    chart.data.datasets[0].data.push(targetData.min);
    chart.data.datasets[1].data.push(targetData.avg);
    chart.data.datasets[2].data.push(targetData.max);
    chart.data.datasets[3].data.push(targetData.loss);

    while (chart.data.labels.length > maxNumberOfDataPoints) {
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
        chart.data.datasets[1].data.shift();
        chart.data.datasets[2].data.shift();
        chart.data.datasets[3].data.shift();
    }
    
    recalculateMaxValue(chart, chart.data.datasets[2].data);
    
    chart.update();
}

function getCardForChart(chart)
{
    return jQuery(chart.canvas).parents('.card');
}

function updateCardData(card, targetData, defaultValues)
{
    card.data('last-update', targetData.time);
    
    if (targetData == false) {
        targetData = {
            time: card.find('.title-status-table').data('default'),
            min: card.find('.status-data-min').data('default'),
            avg: card.find('.status-data-avg').data('default'),
            max: card.find('.status-data-max').data('default'),
            loss: card.find('.status-data-loss').data('default')
        }
    }
    
    card.find('.title-status-table').text('Status (' + moment(targetData.time * 1000).format('YYYY-MM-DD HH:mm:ss') + ')')
    card.find('.status-data-loss').text(targetData.loss + '%');
    card.find('.status-data-min').text(targetData.min + ' ms');
    card.find('.status-data-avg').text(targetData.avg + ' ms');
    card.find('.status-data-max').text(targetData.max + ' ms');

    if (targetData.status) {
        var iconClasses = '';
        
        if (targetData.status == 'online') {
            iconClasses = 'fa-check-circle has-text-success';
        } else if (targetData.status == 'unstable') {
            iconClasses = 'fa-exclamation-circle has-text-warning';
        } else if (targetData.status == 'offline') {
            iconClasses = 'fa-times-circle has-text-danger';
        }
        
        card.find('.card-icon .fa').attr('class', '').addClass('fa ' + iconClasses);
    }
    
    if (defaultValues && targetData != false) {
        card.find('.title-status-table').data('default', targetData.time);
        card.find('.status-data-loss').data('default', targetData.loss);
        card.find('.status-data-min').data('default', targetData.min);
        card.find('.status-data-avg').data('default', targetData.avg);
        card.find('.status-data-max').data('default', targetData.max);
    }
}

function recalculateMaxValue(chart, maxValues)
{
    var maxValue = Math.max.apply(null, maxValues);
    
    chart.options.scales.yAxes[0].ticks.suggestedMax = maxValue * 1.1;
    
    if (maxValue / 5 < 11) {
        chart.options.scales.yAxes[0].ticks.stepSize = 5;
    }
}
