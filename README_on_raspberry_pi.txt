1. First, specify the static IP on Raspberry Pi by: 

sudo nano /etc/dhcpcd.conf

. Then edit the following:

# Example static IP configuration:
interface eth0
static ip_address=192.168.1.193/24
#static ip6_address=fd51:42f8:caae:d92e::ff/64
static routers=192.168.1.1
#static domain_name_servers=192.168.0.1 8.8.8.8 fd51:42f8:caae:d92e::1
static domain_name_servers=192.168.1.1

2. Second, update numpy first, then install pandas. The original numpy might not be the latest version. Also install xlrd for xlsx file support. pip can be used for all tasks.

3. Third, power on the sensor, then connect the Ethernet cable. After that, the Raspberry Pi will lose WiFi connection. So this step can't be done with remote control over WiFi. (Someone on the forum suggested killing ifplugd by: 

sudo ifplugd eth0 --kill

to prevent switching to Ethernet.) If we do SSH on the Pi via the cable LAN, this should not be a problem. 

4. Then we can run test scripts without problem.