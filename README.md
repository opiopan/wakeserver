Wakeserver
====

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Wakeserver is a server which works as a home automation hub running on Raspberry Pi.
You can controll any devices connected to your home network, such as diagnosing status or terning on / off power.<br>
Wakeserver has not only basic device controll capability, but also a mechanism to expands capability by adding plugin modules. 

## User Interfaces
Wakeserver provides 3 types of user interface.

### Default Web UI
Primery interface is Web UI accessable via port 8080.

<p align="center">
<img alt="default Web UI" src="https://raw.githubusercontent.com/wiki/opiopan/wakeserver/images/ws-web.gif" width=200>
</p>

### Apple Home Kit
Wakeserver contains a plugin for [Homebridge](https://github.com/nfarina/homebridge) to behave as Apple Home Kit accessory. It means you can controll any devices managed by wakeserver through iOS or macOS Home App, and can also controll by ordering to Siri.

<p align="center">
<img alt="Apple Home Kit interface" src="https://raw.githubusercontent.com/wiki/opiopan/wakeserver/images/ws-homekit.gif" width=200>
</p>

### Native App
[Wakeserver Mobile](https://github.com/opiopan/WakeserverMobile) is a iOS and watchOS application. That is the other way to access devices managed by wakeserver.

<p align="center">
<img alt="Native App for Apple Watch" src="https://raw.githubusercontent.com/wiki/opiopan/wakeserver/images/ws-mobile.gif" width=200>
</p>

## Requirement
 * **Node v4.3.2 or grater** is required to run [Homebridge](https://github.com/nfarina/homebridge) 

## Prepare to Install (Personalize)
Before intall Wakeserver, you need to prepare some files correspond to your home network. Several examples are [here](https://github.com/opiopan/wakeserver/tree/master/personal).
Following files should be placed in your configuration directory.

* **wakeserver.conf**: global configuration as JSON (REQUIRED) 
* **servers.conf**: describing device to be managed as JSON (REQUIRED)
* **homebridge/config.json**: configuration file for homebridge (OPTIONAL)
* **html/images/\***: image files correnspondind to each device listed in *wakeserver.conf* (OPTIONAL)
* **plugin.py/\***: plugin module working in wakeserver daemon process (OPTIONAL)<br>
This type of plugin module must be writen in python.
* **plugin/\***: plugin module executing by wakeserver daemon as the other process (OPTIONAL)<br>
## Installation
Please download the latest Wakeserver codes from github.

```shell
$ git clone https://github.com/opiopan/wakeserver.git
```

Then run the configuration script with directory path placed your personalized configuration files.

```shell
$ cd wakeserver
$ ./configure ~/DirPlacedYourConfigurations
```

Finally, install and run wakeserver service.

```shell
$ sudo make install
```

## Related Projects

<img alt="elflet" src="https://raw.githubusercontent.com/wiki/opiopan/wakeserver/images/elflet.jpg" height=350 align="right">

* **[elflet](https://github.com/opiopan/elflet)**:
Home IoT controller based on [ESP-WROOM-32](https://www.espressif.com/en/products/hardware/modules) <br>
By collaborating with this small device, wakeserver will get a capability to controll devices which does not have network connectivity, since elflet can work as IR remote controller. In addition, elflet can interact with devices as BLE HID keyboard.<br>
elflet is also working sensor node. Following sensors are installed:
    * Temperature
    * Humidity
    * Atmospheric Pressure
    * Luminocity


* **[Wakeserver Mobile](https://github.com/opiopan/WakeserverMobile)**: 
iOS / watchOS App to access Wakeserver<br>
This application is fully optimized for  Apple Watch and iPhone.
