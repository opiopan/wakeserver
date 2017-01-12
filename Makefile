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
DAEMON			= $(DAEMON_DIR)/wakeserverd
SERVICE_CONF		= /etc/systemd/system/wakeserver.service

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
ADDOPTION		= tool/addoption

CGIENABLING		= '^<Directory \/var\/www\/>' Options \
			  '\+ExecCGI' '+ExecCGI'

CGIS			= wakeserver-get.cgi wakeserver-wake.cgi \
			  wakeserver-sleep.cgi wakeserver-reboot.cgi \
			  wakeserver-attribute.cgi
PLUGINS			= cannon-printe

PERSONAL		= opiopan

COPIEE_DIRS		= $(SITE_CONF_DIR) $(HTML_DIR) $(SBIN_DIR) \
			  $(PLUGIN_DIR)

all:

install: apache2restart daemonrestart homebridgerestart

apache2restart: copyfiles apache2config
	/etc/init.d/apache2 restart

daemonrestart: $(DAEMON) $(SERVICE_CONF)
	systemctl daemon-reload || exit 1
	systemctl enable wakeserver.service || exit 1
	systemctl restart wakeserver.service || exit 1

homebridgerestart: homebridge-plugin homebridge-config homebridge-service
	systemctl daemon-reload || exit 1
	systemctl enable homebridge.service || exit 1
	systemctl restart homebridge.service || exit 1

homebridge-service: $(HOMEBRIDGE_SERVICE) $(HOMEBRIDGE_DEFAULT) $(HOMEBRIDGE_RUNNER)


copyfiles: $(COPIEE_DIRS) $(WAKEONLAN) daemon commands
	cp apache-conf/wakeserver.conf $(SITE_CONF_DIR) || exit 1
	cp -R html/* $(HTML_DIR) || exit 1
	for f in $(CGIS);do \
	    $(INSTALL) -m755 cgi-bin/$$f $(CGI_DIR)/$$f || exit 1; \
	done
	$(INSTALL) -m 4755 sbin/sussh $(SBIN_DIR)/sussh || exit 1
	cp -R personal/$(PERSONAL)/* $(BASE_DIR) || exit 1

commands: sbin
	make -C src

intermediate sbin $(SBIN_DIR):
	mkdir $@

daemon: $(DAEMON) $(SERVICE_CONF)

$(DAEMON): daemon/wakeserverd $(DAEMON_DIR)
	$(INSTALL) -m755 $< $@

$(SERVICE_CONF): daemon/wakeserver.service
	$(INSTALL) -m644 $< $@

$(HTML_DIR) $(DAEMON_DIR) $(PLUGIN_DIR):
	$(INSTALL) -d $@

apache2config: $(SITE_CONF_DIR)
	mv $(PORTS_CONF) $(PORTS_CONF).bak || exit 1
	grep -v ' 8080$$' $(PORTS_CONF).bak > $(PORTS_CONF) || exit 1
	echo 'Listen 8080' >> $(PORTS_CONF) || exit 1
	mv $(MIME_CONF) $(MIME_CONF).bak || exit 1
	cat $(MIME_CONF).bak | $(UNCOMMENT) '\.cgi$$' > $(MIME_CONF) || exit 1
	a2enmod cgi || exit 1
	a2ensite wakeserver || exit 1

$(SITE_CONF_DIR):
	apt-get -y install apache2

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
