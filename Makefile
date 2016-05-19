APACHE_CONF		= /etc/apache2/apache2.conf
PORTS_CONF		= /etc/apache2/ports.conf
MIME_CONF		= /etc/apache2/mods-available/mime.conf
SITE_CONF_DIR		= /etc/apache2/sites-available
SERVERS_DIR		= /var/www/wakeserver
HTML_DIR		= /var/www/wakeserver/html
CGI_DIR			= /usr/lib/cgi-bin
DAEMON_DIR		= /var/www/wakeserver/daemon
DAEMON			= $(DAEMON_DIR)/wakeserverd
SERVICE_CONF		= /etc/systemd/system/wakeserver.service

WAKEONLAN		= /usr/bin/wakeonlan

INSTALL			= install $(INSTALL_OPT)
INSTALL_OPT		= -o root -g root
UNCOMMENT		= tool/uncomment
ADDOPTION		= tool/addoption

CGIENABLING		= '^<Directory \/var\/www\/>' Options \
			  '\+ExecCGI' '+ExecCGI'

CGIS			= wakeserver-get.cgi wakeserver-wake.cgi

all:

install: apache2restart daemonrestart

apache2restart: copyfiles apache2config
	/etc/init.d/apache2 restart

daemonrestart: $(DAEMON) $(SERVICE_CONF)
	systemctl daemon-reload || exit 1
	systemctl restart wakeserver.service || exit 1

copyfiles: $(SITE_CONF_DIR) $(HTML_DIR) $(WAKEONLAN) daemon
	cp apache-conf/wakeserver.conf $(SITE_CONF_DIR) || exit 1
	cp conf/servers.conf $(SERVERS_DIR) || exit 1
	cp -R html/* $(HTML_DIR) || exit 1
	for f in $(CGIS);do \
	    $(INSTALL) -m755 cgi-bin/$$f $(CGI_DIR)/$$f || exit 1; \
	done

daemon: $(DAEMON) $(SERVICE_CONF)

$(DAEMON): daemon/wakeserverd $(DAEMON_DIR)
	$(INSTALL) -m755 $< $@

$(DAEMON_DIR):
	$(INSTALL) -d $@

$(SERVICE_CONF): daemon/wakeserver.service
	$(INSTALL) $< $@

$(HTML_DIR):
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
