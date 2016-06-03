var UPDATE_INTERVAL = 2000;
var UPDATE_INTERVAL_ERROR = 5000;
var TRANSITION_TIMEOUT = 120 * 1000;
var transitCount = 0;

var defaults = {
    "confirm-wake-up": 'true',
    "confirm-shut-down": 'true'
};

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
	// set up inital state of controls in drawer menu
	//---------------------------------------------------
	reflectToToggleMenu('confirm-wake-up');
	reflectToToggleMenu('confirm-shut-down');
	
	//---------------------------------------------------
	// respond to click each server
	//---------------------------------------------------
	$(document).on('click', '.server-entry', function(){
	    var $indicator = $(this).find('.on-indicator');
	    var offState = $indicator.hasClass('off-state');
	    var transitToOn = $indicator.hasClass('transit-to-on');
	    if (offState && !transitToOn){
		var message = 
		    "Are you sure to wake up a server '" + this.id + "' ?";
		var param = {
		    title: "Wake up a Server",
		    message: message,
		    buttons: YesNoDialog,
		    definitive: configValue('confirm-wake-up') != 'true',
		    definitiveValue: "Yes"
		};
		var target = this.id;
		popupDialog(param, function(result){
		    if (result != 'Yes') return;
		    
		    var url = 'cgi-bin/wakeserver-wake.cgi';
		    var param = {"target" : target};
		    $.post(url, param, function(data) {
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
		});
	    }else if (!offState && !transitToOn){
		var message = 
		    "Are you sure to stop a server '" + this.id + "' ?";
		var param = {
		    title: "Stop a Server",
		    message: message,
		    buttons: YesNoDialog,
		    definitive: configValue('confirm-shut-down') != 'true',
		    definitiveValue: "Yes"
		};
		var target = this.id;
		popupDialog(param, function(result){
		    if (result != 'Yes') return;

		    $.ajax({
		        type: "POST",
			url: 'cgi-bin/wakeserver-sleep.cgi',
			data: {"target" : target},
			scriptCharset: 'utf-8',
			dataType:'json',
			success: function(result) {
			    if (!result.result){
				var param = {
				title: "Fail to stop a server",
				message: result.message,
				buttons: OkDialog,
				definitive: false,
				definitiveValue: false
				};
				popupDialog(param);
				$indicator.removeClass('transit-to-on');
			    }
			}
		    });

		    var counter = transitCount++;
		    $indicator.attr('transit-counter', counter);
		    $indicator.addClass('transit-to-on');
		    setTimeout(function(){
			if ($indicator.attr('transit-counter') == counter){
			    $indicator.removeClass('transit-to-on');
			}
		    }, TRANSITION_TIMEOUT);
		});
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
		resetAboutSheet();
		$close = $menu;
	    }
	});

	$(document).on('click', '.modal', function(){
	    var $modal = $('.modal');
	    $close.removeClass('menu-open');
	    $modal.removeClass('modal-inactive');
	    $close = $();
	});

	$(document).on('click', '.menu-item', function(){
	    if (this.id == 'confirm-wake-up' || 
		this.id == 'confirm-shut-down'){
		toggleMenu($(this));
	    }else if (this.id == 'about-service'){
		showAboutSheet();
	    }else{
		var param = {
		    title: "Not implemented",
		    message: "Please wait releasing a new revision " + 
			     "which implement this feature.",
		    buttons: OkDialog,
		    definitive: false,
		    definitiveValue: false
		};
		popupDialog(param);
	    }
	});

	//---------------------------------------------------
	// SVG load
	//---------------------------------------------------
	$('.svg-placeholder').each(function(){
	    var $placeholder = $(this);
	    var svg = $placeholder.attr("svg-path");
	    $placeholder.load(svg + " svg", function(){
		var $this = $(this);
		if ($this.hasClass("svg-animate")){
		    initSvgAnimation(this);
		}; 
	    });
	});

	//---------------------------------------------------
	// reset about sheet
	//---------------------------------------------------
	resetAboutSheet();
	
	return false;
    });
})(jQuery);


//---------------------------------------------------
// functions to update server entry
//---------------------------------------------------
function updateServerState(){
    (function($) {
	$.ajax({
	    type: "GET",
	    url: 'cgi-bin/wakeserver-get.cgi',
	    scriptCharset: 'utf-8',
	    dataType:'json',
	    success: function(servers) {
		var i = 0;
		$('.server-list .server-entry').each(function() {
		    applyServerState($(this), servers[i]);
		    i++;
		});
		$('header .logo').removeClass('error-logo');
		setTimeout("updateServerState()", UPDATE_INTERVAL);
	    },
	    error: function(xhr, textStatus, errorThrown) {
		$('header .logo').addClass('error-logo');
		setTimeout("updateServerState()", UPDATE_INTERVAL_ERROR);
	    }
	});
    })(jQuery);
}

function applyServerState($node, server){
    (function($) {
	var $indicator = $node.find('.on-indicator');
	var inOffState = $indicator.hasClass('off-state');
	if (inOffState && server.status == 'on'){
	    $indicator.removeClass('off-state');
	    $indicator.removeClass('transit-to-on');
	}else if (!inOffState && server.status == 'off'){
	    $indicator.addClass('off-state');
	    $indicator.removeClass('transit-to-on');
	}
    })(jQuery);
}

//---------------------------------------------------
// confirmation dialog
//---------------------------------------------------

var YesNoDialog = [{
    name: "Yes",
    isDefault: false,
},{
    name: "No",
    isDefault: true,
}];

var OkDialog = [{
    name: 'OK',
    isDefault: true
}];

function popupDialog(params, callback){
    (function($) {
	if (params.definitive){
	    if (callback){
		callback(params.definitiveValue);
	    }
	}else{
	    $dialog = $('#popup-dialog')
	    if ($dialog.hasClass('modal-active')){
		if (callback){
		    callback(null);
		}
	    }else{
		$frame = $dialog.find('.dialog-frame');
		$title = $frame.find('.title').empty();
		$message = $frame.find('.message').empty();
		$placeholder = $frame.find('.button-placeholder').empty();

		$title.append(params.title);
		$message.append(params.message.replace(/\n/g, "<br>"));
		var i;
		for (i in params.buttons){
		    var button = params.buttons[i];
		    var $button = $('<div/>').append(button.name);
		    $button.addClass('button');
		    $button.attr('button-id', button.name);
		    if (button.isDefault){
			$button.addClass('default-button');
		    }
		    $placeholder.append($button);
		}
		$placeholder.find('.button')
		    .css('width', '' + 100 / params.buttons.length + '%');

		$dialog.find('.button').on('click', function(){
		    $dialog.find('.button').off('click');
		    $dialog.removeClass('modal-active');
		    if (callback){
			callback($(this).attr('button-id'));
		    }
		});

		$dialog.addClass('modal-active');
	    }
	}
    })(jQuery);
}

//---------------------------------------------------
// toggle switch
//---------------------------------------------------
function configValue(nodeid){
    var value = localStorage.getItem(nodeid);
    if (!value){
	value = defaults[nodeid];
    }

    return value;
}

function reflectToToggleMenu(nodeid){
    (function($) {
	var value = configValue(nodeid);
	var $node = $('#' + nodeid);
	$node.removeClass('toggle-on');
	if (value == 'true'){
	    $node.addClass('toggle-on');
	}
    })(jQuery);
}

function toggleMenu($node){
    (function($) {
	var key = $node.attr("id");
	var value;
	if ($node.hasClass('toggle-on')){
	    $node.removeClass('toggle-on');
	    value = 'false';
	}else{
	    $node.addClass('toggle-on');
	    value = 'true';
	}
	localStorage.setItem(key, value);
    })(jQuery);
}

//---------------------------------------------------
// SVG animation
//---------------------------------------------------
function initSvgAnimation(node){
    paths = new Array();
    var totalLength = 0;
    [].slice.call(node.querySelectorAll('path')).forEach(function(path, i){
	paths[i] = {node: path, length: path.getTotalLength()};
	totalLength += paths[i].length;
    });

    var currentLength = 0;
    for (i = 0; i < paths.length; i++){
	paths[i].node.style.strokeDasharray = 
	    (totalLength - currentLength) + ' ' + 
	    (totalLength + currentLength);
	paths[i].node.style.strokeDashoffset = totalLength;

	currentLength += paths[i].length;
    }
}

//---------------------------------------------------
// about sheet
//---------------------------------------------------
var aboutSheetPhase = 0;

function resetAboutSheet(){
    (function($) {
	$('.about-sheet').removeClass('about-sheet-show');
    })(jQuery);
}

function showAboutSheet(){
    (function($) {
	$('.about-sheet .hidable').addClass('hide');
	$('.about-sheet .svg-animate').removeClass('svg-draw');
	$('.about-sheet').addClass('about-sheet-show');
	aboutSheetPhase = 0;
	transitAboutSheet();
    })(jQuery);
}

var aboutSheetTransitionCount = 0;

function transitAboutSheet(hash){
    (function($) {
        if (hash && hash != aboutSheetTransitionCount){
	    return;
        }
	if (!$('.about-sheet').hasClass('about-sheet-show')){
	    return;
	}
	
	aboutSheetPhase++;
	
	if (aboutSheetPhase == 1){
            aboutSheetTransitionCount++;
            hash = aboutSheetTransitionCount;
	    setTimeout(function(){transitAboutSheet(hash);}, 800);
	}else if (aboutSheetPhase == 2){
	    $('.about-sheet .title').removeClass('hide');
	    setTimeout(function(){transitAboutSheet(hash);}, 700);
	}else if (aboutSheetPhase == 3){
	    $('.raspi-line').addClass('svg-draw');
	    setTimeout(function(){transitAboutSheet(hash);}, 6300);
	}else if (aboutSheetPhase == 4){
	    $('.raspi-image').removeClass('hide');
	    setTimeout(function(){transitAboutSheet(hash);}, 1200);
	}else if (aboutSheetPhase == 5){
	    $('.raspi-title').removeClass('hide');
	    $('.about-sheet .remark').removeClass('hide');
	}	
    })(jQuery);
}
