var fs = require('fs');
var request = require('request');
var webweather = require('./util/webweather.js');

var CONFIG = '/run/wakeserver/status.full';
var STATUS = '/run/wakeserver/status';
var Service, Characteristic, Accessory, uuid;

//============================================================================
//  Exports block
//============================================================================
module.exports = function(homebridge) {
    //--------------------------------------------------
    //  Setup the global vars
    //--------------------------------------------------
    Service = homebridge.hap.Service;
    Characteristic = homebridge.hap.Characteristic;
    Accessory = homebridge.hap.Accessory;
    uuid = homebridge.hap.uuid;

    //--------------------------------------------------
    //  Register ourselfs with homebridge
    //--------------------------------------------------
    homebridge.registerPlatform("homebridge-wakeserver", "Wakeserver", 
				WSPlatform);
};

//============================================================================
//  Wakeserver Platform
//============================================================================
function WSPlatform(log, config) {
    this.log = log;
    this.wakeserver = new Wakeserver(this.log);
    this.servers = this.wakeserver.servers;

    this.config = config;
    this.enableOnlySwitch = config.enableOnlySwitch;
    this.ignoreServers = config.ignoreServers;
}


// Invokes callback(accessories[])
WSPlatform.prototype.accessories = function(callback) {
    var i = 0;
    var accesories = [];
    for (i = 0; i < this.servers.length; i++){
	var server = this.servers[i];
	var scheme = server.config.scheme;
	if (!this.enableOnlySwitch || (scheme.on && scheme.off)){
	    if (this.ignoreServers.indexOf(server.config.name) == -1){
		var a = new WSAccessory(server);
		accesories.push(a);
		if (server.config.scheme.volume){
		    var a = new WSAccessory(server, 'volume');
		    accesories.push(a);
		}
		if (server.config.scheme.tvchannel){
		    accesories.push(new WSAccessory(server, 'tvchannel'));
		    accesories.push(
			new WSAccessory(server, 'tvband:terrestrial'));
		    accesories.push(new WSAccessory(server, 'tvband:bs'));
		    accesories.push(new WSAccessory(server, 'tvband:cs'));
		}
	    }
	}
    }

    var customs = this.config.accessories;
    for (i = 0; customs && i < customs.length; i++){
	var a = new CustomAccessory(this.wakeserver, customs[i]);
	accesories.push(a);
    }

    callback(accesories);
}

//============================================================================
// Accessory for Wakeserver
//============================================================================
function WSAccessory(server, type){
    this.server = server;
    this.log = this.server.wakeserver.log;
    this.config = server.config;
    this.index = server.index;
    this.name = this.config.name;
    this.sid = this.config.macaddr;
    this.model = 
	typeof(this.config.comment) != "undefined" ? 
	this.config.comment : undefined;
    this.manufacturer = 
	typeof(this.config.maker) != "undefined" ? 
	this.config.maker : undefined;

    if (type){
	this.name = this.name + ":" + type;
    }

    var service;
    if (type == 'volume' || type == 'tvchannel'){
	//--------------------------------------------------
	//  Volume / Channel accessory
	//--------------------------------------------------
	this.atype = type;

	service = new Service.Lightbulb(this.name);
	this.log.info(this.name + ': Add '+ this.atype + ' characteristic');

	var On = service.getCharacteristic(Characteristic.On);
	On.on('get', function(cb){
	    var status = this.server.getState();
	    this.log.info(this.name + ":On:get: " + status);
	    cb(null, status);
	}.bind(this));
	On.on('set', function(state, cb){
	    this.log.info(this.name + ":On:set " + state);
	    cb(null);
	}.bind(this));
	
	var volume = service.getCharacteristic(Characteristic.Brightness);
	volume.on('get',function(cb){
	    this.log.info(this.name + ':' + this.atype + ':get:');
	    this.server.setgetAttribute(this.atype, null, function(e, v){
		cb(e, Number(v));
	    }.bind(this));
	}.bind(this));
	volume.on('set',function(value, cb){
	    this.log.info(this.name + ':' + this.atype + ':set: ' + value);
	    this.server.setgetAttribute(this.atype, value, cb);
	}.bind(this));
    }else if (type && type.lastIndexOf('tvband:', 0) == 0){
	//--------------------------------------------------
	//  TV band selector accessory
	//--------------------------------------------------
	this.band = type.slice(7);
	
	service = new Service.Switch(this.name);
	this.log.info(this.name + ': Add '+ this.band + ' characteristic');

	var On = service.getCharacteristic(Characteristic.On);
	On.on('get', function(cb){
	    this.log.info(this.name + ':' + this.band + ':get:');
	    this.server.setgetAttribute('tvband', null, function(e, v){
		cb(e, v == this.band);
	    }.bind(this));
	}.bind(this));
	On.on('set', function(state, cb){
	    this.log.info(this.name + ':' + this.band + ':set: ' + state);
	    if (state){
		this.server.setgetAttribute('tvband', this.band, cb);
	    }else{
		cb(null);
	    }
	}.bind(this));
    }else{
	//--------------------------------------------------
	//  Normal accessory
	//--------------------------------------------------
	service = new Service.Switch(this.name);

	var On = service.getCharacteristic(Characteristic.On);
	On.on('get', function(cb){
	    var status = this.server.getState();
	    this.log.info(this.name + ":On:get: " + status);
	    cb(null, status);
	}.bind(this));

	On.on('set', function(state, cb){
	    this.log.info(this.name + ":On:set " + state);
	    var scheme = this.server.config.scheme;
	    if ((state && scheme.on) || (!state && scheme.off)){
		this.server.setPowerState(state);
		cb(null);
	    }else{
		cb("couldn't operate power");
	    }
	}.bind(this));
    }

    this.service = service;
}

WSAccessory.prototype.getServices = function() {
    var services = [];
    var service = new Service.AccessoryInformation();
    service.setCharacteristic(Characteristic.Name, this.name)
        .setCharacteristic(Characteristic.Manufacturer, this.manufacturer)
        .setCharacteristic(Characteristic.Model, this.model)
        .setCharacteristic(Characteristic.SerialNumber, this.sid)
        .setCharacteristic(Characteristic.FirmwareRevision, '1.0.0')
        .setCharacteristic(Characteristic.HardwareRevision, '1.0.0');
    services.push(service);
    services.push(this.service);
    return services;
}

//============================================================================
// Custom accessory
//============================================================================
function CustomAccessory(wakeserver, config) {
    //wakeserver.log.info('CustomAccessory:' + config);
    this.config = config;
    this.wakeserver = wakeserver;
    this.log = this.wakeserver.log;
    this.name = config.name;
    this.type = config.type;
    this.services = [];

    if (this.type == 'psensor'){
	var s = new Service.TemperatureSensor(this.name);
	var c = s.getCharacteristic(Characteristic.CurrentTemperature);
	if (this.config.web){
	    this.weather = new webweather(
		this.log, 
		this.config.web.areaCode, this.config.web.groupCode);
	    c.on('get', function(cb){
		this.log.info(this.name + ":get");
		cb(null, this.weather.temperature);
	    }.bind(this));
	}else{
	    c.value = config.temperature;
	}
	this.services.push(s);
    }else if (this.type == 'attribute'){
	this.onAttribute = config.on.attribute;
	this.onValue = config.on.value;
	this.offAttribute = config.off.attribute;
	this,offValue = config.off.value;
	var servers = this.wakeserver.servers
	var i;
	for (i = 0; i < servers.length; i++){
	    if (servers[i].config.name == config.server){
		this.server = servers[i];
		break;
	    }
	}
	
	var s = new Service.Switch(this.name);
	var c = s.getCharacteristic(Characteristic.On);
	c.on('set', function(state, cb){
	    this.log.info(this.name + ":On:set " + state);
	    if (state){
		this.server.setgetAttribute(
		    this.onAttribute, this.onValue, function(){});
	    }else{
		this.server.setgetAttribute(
		    this.offAttribute, this.offValue, function(){});
	    }
	    cb(null);
	}.bind(this));
	this.services.push(s);
    }
}

CustomAccessory.prototype.getServices = function(){
    var service = new Service.AccessoryInformation();
    service.setCharacteristic(Characteristic.Name, this.name)
        .setCharacteristic(Characteristic.Manufacturer, 'opiopan')
        .setCharacteristic(Characteristic.Model, 'Wakeserver')
        .setCharacteristic(Characteristic.SerialNumber, '00:00:00:00')
        .setCharacteristic(Characteristic.FirmwareRevision, '1.0.0')
        .setCharacteristic(Characteristic.HardwareRevision, '1.0.0');
    this.services.push(service);
    return this.services;
}

//============================================================================
//  wakeserver abstractor
//============================================================================
function Wakeserver(log){
    this.log = log;
    var config = JSON.parse(fs.readFileSync(CONFIG, 'utf8'));

    this.servers = [];
    this.statuses = JSON.parse(fs.readFileSync(STATUS, 'utf8'));

    index =0;
    for (var i = 0; i < config.length; i++){
	var entry = config[i];
	if (entry.groupName){
	    var group = entry;
	    for (var j = 0; j < group.servers.length; j++){
		var serverConfig = group.servers[j];
		var server = new Server(this, index, serverConfig);
		this.servers.push(server);
		index++;
	    }
	}else{
	    var server = new Server(this, index, entry);
	    this.servers.push(seerver);
	    index++;
	}
    }

    this.interval = setInterval(function(){
	//this.log.info('update status');
	this.statuses = JSON.parse(fs.readFileSync(STATUS, 'utf8'));
    }.bind(this), 1000);
}

function Server(wakeserver, index, config) {
    this.wakeserver = wakeserver;
    this.index = index;
    this.config = config;
}

Server.prototype = {
    getState: function() {
	return this.wakeserver.statuses[this.index].status == "on";
    },

    setPowerState: function(state) {
	var url = 'http://localhost:8080/cgi-bin/';
	url += state ? 'wakeserver-wake.cgi' : 'wakeserver-sleep.cgi';
	request({
	    url: url,
	    method: 'POST',
	    form: {
		'target': this.config.name
	    }
	}, function(error, response, body) {
	    this.wakeserver.log.info('setPowerState: finished: ' 
				     + error + ' : ' + body);
	}.bind(this));
    },

    setgetAttribute: function(attribute, value, cb){
	this.wakeserver.log.info('setgetAttribute:' + attribute + ':' + value);

	var target = this.config.name;
	var attrconf = this.config.scheme[attribute];
	if (attrconf && attrconf.lastIndexOf('relay:', 0) == 0){
	    target = attrconf.slice(6);
	}
	var form = {
	    'target': target,
	    'attribute': attribute,
	};
	if (value){
	    form.value = value;
	}
	request({
	    url: 'http://localhost:8080/cgi-bin/wakeserver-attribute.cgi',
	    method: 'POST',
	    form: form
	}, function(error, response, body) {
	    this.wakeserver.log.info('setgetAttribute: '
				     + error + ' : ' + body);
	    if (!error){
		json = JSON.parse(body);
		if (json.value){
		    cb(null, json.value);
		    return
		}
	    }
	    cb(error, null);
	}.bind(this));
    }
}
