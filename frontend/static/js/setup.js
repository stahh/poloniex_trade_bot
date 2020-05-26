$(document).ready(function () {

    $('select').addClass('browser-default');
    user_pair_id = '';
    pair_id = $('.pair_tr').data('pair-id');
    $('.pair_tr[data-pair-id=' + pair_id + ']').addClass('active_pair');
    var main_coin = $('.tabs a.active').text();
    var second_coin = $('.pair_tr[data-pair-id=' + pair_id + ']').children('td:eq(0)').text();
    document.title = main_coin + "/" + second_coin;
    $('#preview_coins h5 b').text(main_coin + '_' + second_coin);
    intervale = $('#buttons .candlestick').data('intervale');
//    zoom = $('#buttons-zoom .zoom').data('zoom');
    zoom = 6;
    draw_graph();

    $('.pair_tr').on('click', function () {
        var main_coin = $('.tabs a.active').text();
        var second_coin = $(this).children('td:eq(0)').text();
        document.title = main_coin + "/" + second_coin;
        $('#preview_coins h5 b').text(main_coin + '_' + second_coin);
        $('.pair_tr').removeClass('active_pair');
        $('#user_pair').empty();
        $(this).addClass('active_pair');
        if ($(this).data('pair-id') != pair_id) {
            pair_id = $(this).data('pair-id');
            draw_graph();
        }
    });

    $('#buttons .candlestick').on('click', function () {
        $('#buttons div .candlestick').removeClass('green');
        $(this).addClass('green');
        intervale = $(this).data('intervale');
        draw_graph();
    });

    $('#buttons-zoom .zoom').on('click', function () {
        $('#buttons-zoom div .zoom').removeClass('green');
        $(this).addClass('green');
        zoom = $(this).data('zoom');
        draw_graph();
    });


    $('.tooltipped').tooltip({
        delay: 50,
        html: true
    });
    $('.add_coin').on('click', function (e) {
        var post_data = $(this).parent('form').serialize();
        $.ajax({
                url: '/trade/addusercoin/',
                dataType: 'html',
                type: 'post',
                cache: false,
                data: post_data,
                success: function (data) {
                console.log('ok');
                    $('#user_trade_pairs').html(data);
                },
                error: function(data) {
                    console.log('Error ' + data);
                }
            });
    });

//    $('.submit_share').on('click', function (e) {
//        var post_form = $(this).closest("form").serialize();
//        $.ajax({
//                url: '/trade/set_share/',
//                dataType: 'html',
//                type: 'post',
//                cache: false,
//                data: post_form,
//                success: function (data) {
//                console.log('ok');
//                    $('#user_trade_pairs').html(data);
//                },
//                error: function(data) {
//                    console.log('Error ' + data);
//                }
//            });
//    });

    $('.rank-up').on('click', function () {
        var user_pair_id = $(this).parent('td').parent('tr').data('pair-id');
        change_rank(user_pair_id, 'up');
    });
    $('.rank-down').on('click', function () {
        var user_pair_id = $(this).parent('td').parent('tr').data('pair-id');
        change_rank(user_pair_id, 'down');
    });

    function change_rank(pair_id, type) {
        $.ajax({
            url: '/trade/changerank/',
            dataType: 'html',
            type: 'post',
            cache: !1,
            data: {
                pair_id: pair_id,
                csrfmiddlewaretoken: getCookie('csrftoken'),
                type: type
            },
            success: function (data) {
                if ('false' === data) {
                    Materialize.toast('Error while changing rank', 1000)
                } else if ('ok' === data) {
                    location.reload();
                }
            }
        })
    }


    $('.pair-share').keypress(function (e) {
        if (e.which === 13) {
            var share = $(this).val();
            var user_exch = $('#exchange').val();
            if ('' !== share) {
                var user_pair_id = $(this).parent('td').parent('tr').data('pair-id');
                $.post('/trade/set_share/', {
                        pair_id: user_pair_id,
                        share: share,
                        user_exch: user_exch,
                        csrfmiddlewaretoken: getCookie('csrftoken')
                    },
                    function (data) {
                        'ok' === data ? location.reload() : Materialize.toast(data, 1000);
                    });
            }
        }
    }).on('focus', function () {
        $('.collapsible').collapsible('destroy');
    }).on('blur', function () {
        $('.collapsible').collapsible();
    });


    $('#disable-script').on('change', function () {
        $.post('/trade/exchange_script_activity/', {
            user_exch: $('#exchange').val(),
            csrfmiddlewaretoken: getCookie('csrftoken')
        }, function (data) {
            if (data) {
                location.reload()
            } else Materialize.toast('Error while change script status', 1500)
        })
    });
    $('#disable-fake').on('change', function () {
        $.post('/trade/exchange_trade_fake/', {
            user_exch: $('#exchange').val(),
            csrfmiddlewaretoken: getCookie('csrftoken')
        }, function (data) {
            if (data) {
                location.reload()
            } else Materialize.toast('Error while change script status', 1500)
        })
    });
    $('.change-primary-coin-status').on('change', function () {
        var pc = $(this).parent('.primary-coin').data('primary-coin');
        $.post('/trade/change_primary_coin/', {
            user_exch: $('#exchange').val(),
            csrfmiddlewaretoken: getCookie('csrftoken'),
            coin: pc
        }, function (data) {
            'ok' === data ? location.reload() : Materialize.toast('Error while changing status', 1000)
        })
    });

    $('.primary-rank').on('click', function () {
        change_primary_coin($(this).data('type'), $(this).parent('.primary-coin').data('primary-coin'));
    });

    function change_primary_coin(type, coin) {
        $.post('/trade/change_primary_coin_rank/', {
            user_exch: $('#exchange').val(),
            csrfmiddlewaretoken: getCookie('csrftoken'),
            coin: coin,
            type: type
        }, function (data) {
            'ok' === data ? location.reload() : Materialize.toast('Error while changing rank', 1000)
        })
    }

    function get_new_orders_to_trade() {
        $.ajax({
            url: '/trade/get_new_orders_to_trade/',
            type: 'post',
            dataType: 'html',
            data: {
                user_exch: $('#exchange').val(),
                csrfmiddlewaretoken: getCookie('csrftoken'),
                already: $('.orders_to_trade').length
            },
            success: function (data) {

                //console.log(data)
                $( "#user_orders" ).load(window.location.href + " #user_orders" );
        $( "#calculated_to_trade" ).load(window.location.href + " #calculated_to_trade" );

            }
        })
    }

    function get_new_fake_orders_to_trade() {
        $.ajax({
            url: '/trade/get_new_fake_orders_to_trade/',
            type: 'post',
            dataType: 'html',
            data: {
                user_exch: $('#exchange').val(),
                csrfmiddlewaretoken: getCookie('csrftoken'),
                already: $('.orders_to_trade_fake').length
            },
            success: function (data) {

                //console.log(data)
                $( "#user_orders_fake" ).load(window.location.href + " #user_orders_fake" );
        $( "#calculated_to_trade_fake" ).load(window.location.href + " #calculated_to_trade_fake" );

            }
        })
    }

    function updateDiv() {
        console.log('update orders');
        $( "#user_orders" ).load(window.location.href + " #user_orders" );
        $( "#calculated_to_trade" ).load(window.location.href + " #calculated_to_trade" );
        $( "#user_orders_fake" ).load(window.location.href + " #user_orders_fake" );
        $( "#calculated_to_trade_fake" ).load(window.location.href + " #calculated_to_trade_fake" );
    }

    setInterval(draw_graph, 60000);


    $('#user_orders').DataTable();
    $('#calculated_to_trade').DataTable();
    $.extend($.fn.dataTable.defaults, {
        searching: false,
        ordering: false
    });

    $('#user_orders_fake').DataTable();
    $('#calculated_to_trade_fake').DataTable();
    $.extend($.fn.dataTable.defaults, {
        searching: false,
        ordering: false
    });


    function cl(value) {
        console.log(value)
    }

});

var ticker = {};

//socket = new WebSocket("ws://" + window.location.host + "/trade/");
//socket.onmessage = function (message) {
//    var item = JSON.parse(message.data);
//    if (item.pair_id in ticker) {
//        if (item.last !== ticker[item.pair_id].last) {
//            ticker[item.pair_id].last = item.last;
//            ticker[item.pair_id].percent = item.percent;
//        }
//    } else {
//        ticker[item.pair_id] = {'last': item.last, 'percent': item.percent}
//    }
//};

setInterval(function () {
    for (var item in ticker) {

        var prev_last = Number($('.pair_last#last_' + item).text());
        if (ticker[item].last > prev_last) {
            $('.pair_last#last_' + item).text(ticker[item].last).parent('tr').addClass('priceChangeUp');
            $('.pair_last#arrow_' + item).html('<i class="fa fa-arrow-up fa-1x green-text" aria-hidden="true"></i>');
        } else if (ticker[item].last < prev_last) {
            $('.pair_last#last_' + item).text(ticker[item].last).parent('tr').addClass('priceChangeDown');
            $('.pair_last#arrow_' + item).html('<i class="fa fa-arrow-down fa-1x red-text" aria-hidden="true"></i>');
        } else {
            $('.pair_last#arrow_' + item).html('');
        }
        if (ticker[item].percent > 0) {
            $('.pair_last#percent_' + item).text(Math.floor(ticker[item].percent * 100) / 100 + '%').removeClass('red-text').addClass('green-text');
        } else {
            $('.pair_last#percent_' + item).text(Math.floor(ticker[item].percent * 100) / 100 + '%').addClass('red-text').removeClass('green-text');
        }
        setTimeout(function () {
            $('.pair_last').parent('tr').removeClass('priceChangeDown priceChangeUp ');
        }, 600);
    }
}, 2000);

function colorD(ord) {
    if (ord == 'buy'){
        color = 'green';
    }
    if (ord == 'sell'){
        color = 'red';
    }
    return color;
}

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function draw_graph() {
    var ohlcData = [];
    var extremums = [];
    var orders = [];
    var upper_line = [];
    var bottom_line = [];
    $.post('/trade/get_ticker/', {
        user_pair_id: $('#user_pair').text(),
        pair_id: pair_id,
        csrfmiddlewaretoken: getCookie('csrftoken'),
        intervale: intervale,
        zoom: zoom,
        exchange: $('#exchange_id').text()
    }, function (data) {
//        console.log('DATA')
//        console.log(data)
        for (var i = 1; i < data['ticker'].length; i++) {
            ohlcData.push([new Date(Date.parse(data['ticker'][i].date)),
            round(data['ticker'][i].high), round(data['ticker'][i].low),
            round(data['ticker'][i].open), round(data['ticker'][i].close)]);
        }
        for (var j = 0; j < data['extremums'].length; j++) {
            extremums.push([
                new Date(Date.parse(data['extremums'][j][0])),
                round(data['extremums'][j][1]),
                data['extremums'][j][2]
            ]);
        }
        for (var i = 0; i < data['orders'].length; i++) {
            orders.push([new Date(Date.parse(data['orders'][i].date)),
            round(data['orders'][i].price), data['orders'][i].order_type,
            data['orders'][i].order_number,
            round(data['orders'][i].amount),
            round(data['orders'][i].fact_amount),
            round(data['orders'][i].btc_spent)
            ]);
        }
        for (var j = 0; j < data['upper_line'].length; j++) {
            upper_line.push([
                new Date(Date.parse(data['upper_line'][j][0])),
                round(data['upper_line'][j][1])
            ]);
        }
        for (var j = 0; j < data['bottom_line'].length; j++) {
            bottom_line.push([
                new Date(Date.parse(data['bottom_line'][j][0])),
                round(data['bottom_line'][j][1])
            ]);
        }
        var series_data = [];
        series_data.push({
                    type: 'candlestick',
                    data: ohlcData,
                    priceUpFillStyle: '#4caf50',
                    priceDownFillStyle: '#f44336',
                    strokeStyle: 'black',
                    pointWidth: 0.8,
                    stringFormat: '%d'
                });
        if (intervale == 120) {
            series_data.push({
                type: 'line',
                data: upper_line,
                title: 'Upper'
            });
            series_data.push({
                type: 'line',
                data: bottom_line,
                title: 'Bottom'
            });
        }
        if (intervale != 1440){
            series_data.push({
                    type: 'scatter',
                    data: extremums,
                    title: 'Extremum',
                    markers: {
                        size: 10,
                        type: 'triangle',
                        strokeStyle: 'black',
                        lineWidth: 1,
                        fillStyle: 'black'
                    },
                    labels: {
                        fillStyle: 'black',
                        stringFormat: '%d'
                    }
                });
            series_data.push({
                    type: 'scatter',
                    data: orders,
                    title: 'Order',
                    xValuesField: 'date',
                    yValuesField: 'price',
                    markers: {
                        size: 10,
                        type: 'diamond',
                        strokeStyle: 'black',
                        lineWidth: 1,
                        fillStyle: 'yellow'
                    },
                    labels: {
                        fillStyle: 'black',
                        stringFormat: '%d'
                    }
                });
        }


//        console.log('ohlcData')
//        console.log(orders);
        $('#jqChart').jqChart({
            legend: {visible: false},
            border: {lineWidth: 0, padding: 0},
            tooltips: {
                disabled: false,
                type: 'shared',
                borderColor: 'auto',
                snapArea: 100,
                highlighting: true,
                highlightingFillStyle: 'rgba(204, 204, 204, 0.5)',
                highlightingStrokeStyle: 'rgba(204, 204, 204, 0.5)'
            },
            crosshairs: {
                enabled: true,
                hLine: {strokeStyle: '#9c9b96'},
                vLine: {strokeStyle: '#9c9b96'},
                snapToDataPoints: false
            },
            toolbar: {
                visibility: 'visible', // auto, visible, hidden
                resetZoomTooltipText: 'Reset Zoom (100%)',
                zoomingTooltipText: 'Zoom in to selection area',
                panningTooltipText: 'Pan the chart'
            },
            mouseInteractionMode: 'zooming', // zooming, panning
            animation: {duration: 0.0001},
            axes: [
                {
                    type: 'dateTime',
                    location: 'bottom',
                    zoomEnabled: false
                },
                {
                    type: 'linear',
                    location: 'right',
                    zoomEnabled: false
                }
            ],
            shadows: {
                enabled: true
            },

            series: series_data
        });

    }, 'json');
    $('#jqChart').bind('dataPointLabelCreating', function (e, data) {
        var context = data.context;
        data.text = context.dataItem[2];
//        console.log(context)
    });
    user_pair_id = '';
}

function round(d) {
    return Math.round(100000000 * d) / 100000000
}

function submitCoinShare(event) {
    var form_data = $(event).closest("form").serializeArray();
    var post_data = {};
    $(form_data).each(function(index, obj){
        post_data[obj.name] = obj.value;
    });
    post_data['csrfmiddlewaretoken'] = getCookie('csrftoken');
    console.log(post_data['user-exchange']);
    console.log(post_data['coin']);
    console.log(post_data['csrfmiddlewaretoken']);
        $.ajax({

                url: '/trade/set_share/',
                dataType: 'html',
                type: 'post',
                cache: false,
                data: post_data,
                success: function (data) {
                console.log('ok');
                    $('#user_trade_pairs').html(data);
                },
                error: function(data) {
                    console.log('Error ' + data);
                }
            });

}

function deleteUserCoin(e) {
        var user_pair_id = $(e).parent('td').parent('tr').data('pair-id');
           $.ajax({

                url: '/trade/delete_user_pair/',
                dataType: 'html',
                type: 'post',
                cache: false,
                data: {
                    pair_id: user_pair_id,
                    csrfmiddlewaretoken: getCookie('csrftoken')
                },
                success: function (data) {
                console.log('ok');
                    $('#user_trade_pairs').html(data);
                },
                error: function(data) {
                    console.log('Error ' + data);
                }
            });
    }


function getPairChart(e) {
        user_pair_id = $(e).parent().attr('data-pair-id');
        document.title = $(e).text();
        $('#preview_coins h5 b').text($(e).text());
        $('#user_pair').text(user_pair_id)
        draw_graph();
}