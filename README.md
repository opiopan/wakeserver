Wakeserver
====

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
Wakeserver contains a plugin for [Homebridge](https://github.com/nfarina/homebridge) to behave as Apple Home Kit accessory. It means you can controll any devices managed by wakeserver through iOS or macOS Home App, and can controll by ordering to Siri.

<p align="center">
<img alt="default Web UI" src="https://raw.githubusercontent.com/wiki/opiopan/wakeserver/images/ws-homekit.gif" width=200>
</p>

### Native App
[Wakeserver Mobile](https://github.com/opiopan/WakeserverMobile) is a iOS and watchOS application. That is the other way to access devices managed by wakeserver.

<p align="center">
<img alt="default Web UI" src="https://raw.githubusercontent.com/wiki/opiopan/wakeserver/images/ws-mobile.gif" width=200>
</p>

## Requirement
 * **Node v4.3.2 or grater** is required to run [Homebridge](https://github.com/nfarina/homebridge) 

## Prepare to Install (Personalize)
Before intall Wakeserver, you need to prepare some files correspond to your home network. Several examples are [here](https://github.com/opiopan/wakeserver/tree/master/personal).

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
* **[elflet](https://github.com/opiopan/elflet)**:
Home IoT controller based on [ESP-WROOM-32](https://www.espressif.com/en/products/hardware/modules) <br>
By collaborating with this small device, wakeserver will get a capability to controll devices which does not have network connectivity, since elflet can work as IR remote controller.

* **[Wakeserver Mobile](https://github.com/opiopan/WakeserverMobile)**: 
iOS / watchOS App to access Wakeserver<br>
This application is fully optimized for  iWatch and iPhone.

## Licence
Copylight (c) 2016-2019 opiopan [opiopan@gmail.com](mailto:opiopan@gmail.com), 
Licensed under [Apache License Version 2.0 January 2004](http://www.apache.org/licenses/LICENSE-2.0)
