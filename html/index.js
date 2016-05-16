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
		    .append('IP addrress: ' + json[i].ipaddr);
		$('<p/>').appendTo($description)
		    .append('MAC addrress: ' + json[i].macaddr);

		$node.find('.icon span').css({
		    'background-image': "url('" + json[i].icon + "')"
		});
		
		$('.server-list').append($node);
	    }
	});

	$(document).on('click', '.server-entry', function(){
	    var param = {"target" : this.id};
	    $.post('cgi-bin/wakeserver-wake.cgi', param, function(data) {
		var foo = data;
	    });
	});
	
	return false;
    });

})(jQuery);
