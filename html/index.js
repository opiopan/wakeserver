var UPDATE_INTERVAL = 2000;
var TRANSITION_TIMEOUT = 120 * 1000;
var transitCount = 0;

(function($) {
    $(document).ready(function(){

	//---------------------------------------------------
	// main contents creation & update
	//---------------------------------------------------
	var $template = $('#server-entry-template .server-entry');

	$.get('cgi-bin/wakeserver-get.cgi', '', function(text){
	    var json = JSON.parse(text);
	    for (var i in json) {
		var $node = $template.clone(true);
		$node.attr('id', json[i].name);

		var $description = $node.find('.description')
		$('<h1/>').appendTo($description).append(json[i].name);
		$('<p/>').appendTo($description).append(json[i].comment);
		$('<p/>').appendTo($description)
		    .append('IP: ' + json[i].ipaddr);
		$('<p/>').appendTo($description)
		    .append('MAC: ' + json[i].macaddr);

		$node.find('.icon span').css({
		    'background-image': "url('" + json[i].icon + "')"
		});

		applyServerState($node, json[i]);

		$('.server-list').append($node);
	    }
	});

	setTimeout("updateServerState()", UPDATE_INTERVAL);

	//---------------------------------------------------
	// respond to click each server
	//---------------------------------------------------
	$(document).on('click', '.server-entry', function(){
	    $indicator = $(this).find('.on-indicator');
	    var offState = $indicator.hasClass('off-state');
	    var transitToOn = $indicator.hasClass('transit-to-on');
	    if (offState && !transitToOn){
		var param = {"target" : this.id};
		$.post('cgi-bin/wakeserver-wake.cgi', param, function(data) {
		    var foo = data;
		});
		var counter = transitCount++;
		$indicator.attr('transit-counter', counter);
		$indicator.addClass('transit-to-on');
		setTimeout(function(){
		    if ($indicator.attr('transit-counter') == counter){
			$indicator.removeClass('transit-to-on');
		    }
		}, TRANSITION_TIMEOUT);
	    }
	});

	//---------------------------------------------------
	// drower menu operation
	//---------------------------------------------------
	var $close = $();

	$(document).on('click', '.menu-btn', function(){
	    $menu = $(this).parent();
	    $modal = $('.modal');
	    if ($menu.hasClass('menu-open')){
		$menu.removeClass('menu-open');
		$modal.removeClass('modal-inactive');
		$close = $();
	    }else{
		$menu.addClass('menu-open');
		$modal.addClass('modal-inactive');
		$close = $menu;
	    }
	});

	$(document).on('click', '.modal', function(){
	    $modal = $('.modal');
	    $close.removeClass('menu-open');
	    $modal.removeClass('modal-inactive');
	    $close = $();
	});

	return false;
    });
})(jQuery);


//---------------------------------------------------
// functions to update server entry
//---------------------------------------------------
function updateServerState(){
    (function($) {
	$.get('cgi-bin/wakeserver-get.cgi', '', function(text){
	    var servers = JSON.parse(text);
	    var i = 0;
	    $('.server-list .server-entry').each(function(){
		applyServerState($(this), servers[i]);		    
		i++;
	    });
	    
	    setTimeout("updateServerState()", UPDATE_INTERVAL);
	});
    })(jQuery);
}

function applyServerState($node, server){
    (function($) {
	$indicator = $node.find('.on-indicator');
	var inOffState = $indicator.hasClass('off-state');
	if (inOffState && server.status == 'on'){
	    $indicator.removeClass('off-state');
	    $indicator.removeClass('transit-to-on');
	}else if (!inOffState && server.status == 'off'){
	    $indicator.addClass('off-state');
	}
    })(jQuery);
}

