var fs = require('fs');
var request = require('request');
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
		var a = new WSAccessory(server, i);
		accesories.push(a);
	    }
	}
    }

    callback(accesories);
}

//============================================================================
// Accessory
//============================================================================
function WSAccessory(server){
    this.server = server;
    this.log = this.server.wakeserver.log;
    this.config = server.config;
    this.index = server.index;
    this.name = this.config.name;
    this.id = this.config.macaddr;
    this.model = 
	typeof(this.config.comment) != "undefined" ? 
	this.config.comment : undefined;
    this.manufacturer = 
	typeof(this.config.maker) != "undefined" ? 
	this.config.maker : undefined;

    var service = new Service.Switch(this.name);

    service.getCharacteristic(Characteristic.On).on('get', function(cb){
	var status = this.server.getState();
	this.log.info(this.name + ":On:get: " + status);
	cb(null, status);
    }.bind(this));

    service.getCharacteristic(Characteristic.On).on('set', function(state, cb){
	this.log.info(this.name + ":On:set " + state);
	var scheme = this.server.config.scheme;
	if ((state && scheme.on) || (!state && scheme.off)){
	    this.server.setPowerState(state);
	    cb(null);
	}else{
	    cb("couldn't operate power");
	}
    }.bind(this));

    this.service = service;
}

WSAccessory.prototype.getServices = function() {
    var services = [];
    var service = new Service.AccessoryInformation();
    service.setCharacteristic(Characteristic.Name, this.name)
        .setCharacteristic(Characteristic.Manufacturer, this.manufacturer)
        .setCharacteristic(Characteristic.Model, this.model)
        .setCharacteristic(Characteristic.SerialNumber, this.id)
        .setCharacteristic(Characteristic.FirmwareRevision, '1.0.0')
        .setCharacteristic(Characteristic.HardwareRevision, '1.0.0');
    services.push(service);
    services.push(this.service);
    return services;
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
    }
}
