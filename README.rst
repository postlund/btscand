Publishes bluetooth devices over MQTT to Home-Assistant
=======================================================
Periodically scans for bluetooth devices and publishes them over MQTT,
following the auto-discovery scheme in Home Assistant. This will make
them automatically appear. Each device is shown with its RSSI (a simple
AR-filter is applied to smooth out the value).

Installation
------------
Start off by running hassbian. Then basically do this as a preparation:

.. code:: bash

   $ sudo -u homeassistant -s
   $ source /srv/homeassistant/bin/activate
   $ pip install bluepy>=1.1.0

Now, clone repo (still as user homeassistant):

.. code:: bash

   $ cd /home/homeassistant
   $ git clone https://github.com/postlund/btscand.git

Back to user pi and fix systemd startup script:

.. code:: bash

   $ exit
   $ cp /home/homeassistant/btscand/btscand.service
   $ chmod +x /home/homeassistant/btscand/btscand

Make sure you define ``mqtt_user``, ``mqtt_password``, ``mqtt_host``,
``mqtt_port`` and ``mqtt_prefix`` in your secrets file (~/.homeassistant/secrets.yaml).

Enable autostart and start the service:

.. code:: bash

   $ sudo systemctl enable btscand
   $ sudo systemctl start btscand

Check status:

.. code:: bash

   $ sudo systemsctl status btscand
     ● btscand.service - btscand
        Loaded: loaded (/etc/systemd/system/btscand.service; enabled)
           Active: active (running) since Tue 2017-07-25 16:52:02 CEST; 1s ago
            Main PID: 21809 (btscand)
               CGroup: /system.slice/btscand.service
                     ├─21809 /bin/bash /home/homeassistant/btscand/btscand
                                ├─21810 /srv/homeassistant/bin/python /home/homeassistant/btscand/btscand.py
                                          └─21818 /srv/homeassistant/lib/python3.4/site-packages/bluepy/bluepy-helper 0

     Jul 25 16:52:02 hassbian systemd[1]: Started btscand.
     Jul 25 16:52:03 hassbian btscand[21809]: INFO:__main__:Connecting...
     Jul 25 16:52:03 hassbian btscand[21809]: INFO:__main__:Connected!

Disclaimer
----------
This is just a small hack and not ready for prime-time in any way, so
documentation is not a priority... Feel free to do whatever you want with this
project.
