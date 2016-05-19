var UPDATE_INTERVAL = 2000;

(function($) {
    $(document).ready(function(){
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

	$(document).on('click', '.server-entry', function(){
	    var param = {"target" : this.id};
	    $.post('cgi-bin/wakeserver-wake.cgi', param, function(data) {
		var foo = data;
	    });
	});

	setTimeout("updateServerState()", UPDATE_INTERVAL);

	return false;
    });
})(jQuery);

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
	}else if (!inOffState && server.status == 'off'){
	    $indicator.addClass('off-state');
	}
    })(jQuery);
}

