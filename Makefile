PORTS_CONF		= /etc/apache2/ports.conf
SERVICE_CONF_DIR	= /etc/apache2/sites-available
HTML_DIR		= /var/www/wakeserver

INSTALL			= install $(INSTALL_OPT)
INSTALL_OPT		= -o root -g root

HTMLS			= 

all:

install: apache2restart

apache2restart: filecopy apache2config
	/etc/init.d/apache2 restart

filecopy: apache2 $(HTML_DIR)
	cp conf/wakeserver.conf $(SERVICE_CONF_DIR) || exit 1
	rm -rf $(HTML_DIR) || exit 1
	mkdir $(HTML_DIR) || exit 1
	cp -R html/* $(HTML_DIR) || exit 1

$(HTML_DIR):
	mkdir $(HTML_DIR)

apache2config: apache2
	mv $(PORTS_CONF) $(PORTS_CONF).bak || exit 1
	grep -v ' 8080$$' $(PORTS_CONF).bak > $(PORTS_CONF) || exit 1
	echo 'Listen 8080' >> $(PORTS_CONF) || exit 1
	a2enconf serve-cgi-bin || exit 1
	a2ensite wakeserver || exit 1

apache2:
	apt-get -y install apache2 wakeonlan