var client = require('cheerio-httpcli');
var URL='http://www.jma.go.jp/jp/amedas_h/today-50196.html'

module.exports = webweather;

function webweather(log, areaCode, groupCode) {
    var self = this;

    self.log = log;
    self.areaCode = areaCode;
    self.groupCode = groupCode;

    self.interval = setInterval(function(){
	self.updateTemperature();
    }, 1000 * 60 * 10);

    self.updateTemperature();
}

webweather.prototype = {

    updateTemperature: function() {
	var self = this;

	var param = {
	    areaCode: self.areaCode,
	    groupCode: self.groupCode
	};
	client.fetch(URL, param, function(error, $, response){
	    if (error){
		self.log.error('webweather:' + error);
		cb(error, null);
	    }else{
		self.log.info('webweather: fetch finished');
		$('#tbl_list tr').each(function(index){
		    if (index > 1){
			$(this).find('td').each(function(index){
			    if (index == 1){
				var content = $(this).text();
				if (content.length > 0 && 
				    content[0] >= '0' && content[0] <= '9' ){
				    self.lastTemperature = Number(content);
				}
			    }
			});
		    }
		});
		self.temperature = self.lastTemperature;
		self.log.info('webweather: ' + self.temperature + ' degree');
	    }
	});
    }

}
