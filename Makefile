APACHE_CONF		= /etc/apache2/apache2.conf
PORTS_CONF		= /etc/apache2/ports.conf
MIME_CONF		= /etc/apache2/mods-available/mime.conf
SITE_CONF_DIR		= /etc/apache2/sites-available
BASE_DIR		= /var/www/wakeserver
HTML_DIR		= /var/www/wakeserver/html
CGI_DIR			= /usr/lib/cgi-bin
SBIN_DIR		= /var/www/wakeserver/sbin
PLUGIN_DIR		= /var/www/wakeserver/plugin
DAEMON_DIR		= /var/www/wakeserver/daemon
DAEMONLIB_DIR		= $(DAEMON_DIR)/wakeserver
DAEMON			= $(DAEMON_DIR)/wakeserverd
SERVICE_CONF		= /etc/systemd/system/wakeserver.service
MQTT_CONF		= /etc/mosquitto/mosquitto.conf

WAKEONLAN		= /usr/bin/wakeonlan
NODEJS			= /usr/bin/nodejs
HOMEBRIDGE		= /usr/bin/homebridge
HOMEBRIDGE_CONF_DIR	= /var/homebridge
HOMEBRIDGE_CONF		= $(HOMEBRIDGE_CONF_DIR)/config.json
HOMEBRIDGE_SERVICE	= /etc/systemd/system/homebridge.service
HOMEBRIDGE_DEFAULT	= /etc/default/homebridge
HOMEBRIDGE_RUNNER	= /var/www/wakeserver/daemon/homebridge.run

INSTALL			= install $(INSTALL_OPT)
INSTALL_OPT		= -o root -g root
UNCOMMENT		= tool/uncomment
COMMENT			= tool/comment
ADDOPTION		= tool/addoption
EXTJSON			= tool/extjson

CGIENABLING		= '^<Directory \/var\/www\/>' Options \
			  '\+ExecCGI' '+ExecCGI'

CGIS			= wakeserver-get.cgi wakeserver-wake.cgi \
			  wakeserver-sleep.cgi wakeserver-reboot.cgi \
			  wakeserver-attribute.cgi wakeserver-config.cgi
PLUGINS			= cannon-printe

PERSONAL		= opiopan
WAKESERVERCONF_SRC	= personal/$(PERSONAL)/wakeserver.conf
SERVERSCONF_SRC		= personal/$(PERSONAL)/servers.conf

COPIEE_DIRS		= $(SITE_CONF_DIR) $(HTML_DIR) $(SBIN_DIR) \
			  $(PLUGIN_DIR)

PIP			= /usr/local/bin/pip
PPKGS			= requests paho-mqtt

INSTALL_TARGET		= apache2restart daemonrestart avahirestart \
			  homebridgerestart mqttrestart pythonpackage

all:

install: $(INSTALL_TARGET)

mqttrestart: $(MQTT_CONF)
	systemctl daemon-reload || exit 1
	systemctl enable mosquitto || exit 1
	systemctl restart mosquitto || exit 1

$(MQTT_CONF):
	apt-get install -y mosquitto
	apt-get install -y mosquitto-clients
	mv $(MQTT_CONF) $(MQTT_CONF).bak
	$(COMMENT) '^log_dest' < $(MQTT_CONF).bak >$(MQTT_CONF) 

avahirestart:
	m4 -D ID="`$(EXTJSON) $(WAKESERVERCONF_SRC) uuid`"\
	   -D DESC="`$(EXTJSON) $(WAKESERVERCONF_SRC) description`"\
	   -D PLATFORM="`$(EXTJSON) $(WAKESERVERCONF_SRC) platform`"\
	   -D CONFIGHASH="`md5sum $(WAKESERVERCONF_SRC) | cut -d' ' -f1`"\
	   -D SERVERSHASH="`md5sum $(SERVERSCONF_SRC) | cut -d' ' -f1`"\
	   avahi/wakeserver.service > /etc/avahi/services/wakeserver.service
	service avahi-daemon restart

apache2restart:
	tool/uninstallapacheenv

daemonrestart: copyfiles $(DAEMON) $(SERVICE_CONF) daemonlib
	systemctl daemon-reload || exit 1
	systemctl enable wakeserver.service || exit 1
	systemctl restart wakeserver.service || exit 1

homebridgerestart: homebridge-plugin homebridge-config homebridge-service
	systemctl daemon-reload || exit 1
	systemctl enable homebridge.service || exit 1
	systemctl restart homebridge.service || exit 1

homebridge-service: $(HOMEBRIDGE_SERVICE) $(HOMEBRIDGE_DEFAULT) $(HOMEBRIDGE_RUNNER)


copyfiles: $(COPIEE_DIRS) $(WAKEONLAN) daemon commands
	cp -R html/* $(HTML_DIR) || exit 1
	$(INSTALL) -m 4755 sbin/sussh $(SBIN_DIR)/sussh || exit 1
	cp -R personal/$(PERSONAL)/* $(BASE_DIR) || exit 1

commands: sbin
	make -C src

intermediate sbin $(SBIN_DIR):
	mkdir $@

daemon: $(DAEMON) $(SERVICE_CONF) daemonlib

$(DAEMON): daemon/wakeserverd $(DAEMON_DIR)
	$(INSTALL) -m755 $< $@

$(SERVICE_CONF): daemon/wakeserver.service
	$(INSTALL) -m644 $< $@

daemonlib: $(DAEMONLIB_DIR)
	for f in daemon/wakeserver/*.py; do \
	    $(INSTALL) -m644 $$f $(DAEMONLIB_DIR) || exit 1; \
	done

$(HTML_DIR) $(DAEMON_DIR) $(DAEMONLIB_DIR) $(PLUGIN_DIR):
	$(INSTALL) -d $@

$(WAKEONLAN):
	apt-get -y install wakeonlan

homebridge-plugin: $(HOMEBRIDGE)
	npm install -g homebridge/homebridge-wakeserver

homebridge-config: $(HOMEBRIDGE_CONF_DIR)
	cp personal/$(PERSONAL)/homebridge/config.json $(HOMEBRIDGE_CONF_DIR)
	chown homebridge $(HOMEBRIDGE_CONF_DIR)/config.json

$(HOMEBRIDGE_DEFAULT): homebridge/homebridge
	$(INSTALL) -m644 $< $@

$(HOMEBRIDGE_SERVICE): homebridge/homebridge.service
	$(INSTALL) -m644 $< $@

$(HOMEBRIDGE_RUNNER): homebridge/homebridge.run
	$(INSTALL) -m755 $< $@

$(HOMEBRIDGE_CONF_DIR):
	useradd --system homebridge
	mkdir $@
	chown homebridge $@

$(HOMEBRIDGE):
	curl -sL https://deb.nodesource.com/setup_6.x | bash -
	apt-get install -y nodejs
	apt-get install -y libavahi-compat-libdnssd-dev
	npm install -g --unsafe-perm homebridge hap-nodejs node-gyp
	cd /usr/lib/node_modules/homebridge || exit 1;\
	npm install --unsafe-perm bignum
	cd /usr/lib/node_modules/hap-nodejs/node_modules/mdns || exit 1;\
	node-gyp BUILDTYPE=Release rebuild

pythonpackage: $(PIP)
	pip install $(PPKGS)

$(PIP):
	curl -kL https://bootstrap.pypa.io/get-pip.py | python
