"""
Author: Chris Knowles
File: secrets.py
Version: 1.0.0
Notes: This file is where you keep secret settings, passwords, and tokens!
       If you put them in the code you risk committing that info or sharing
       it inadvertently
"""

secrets = {
    # FeatherS2 device and Featherwing Airlift ESP32 WiFi related secrets
    "debug_on" : True,
    "i2c_frequency" : 1000000,  # 0 or negative means use default
    "spi_frequency" : 20000000,  # 0 or negative means use defualt
    "use_wifi" : True,
    "use_mqtt" : True,
    "wifi_timeout" : 5,
    "wifi_retries" : 5,  # 0 or negative means try forever
    "ssid" : "DCETLocalVOIP-Pi",
    "password" : "DCETLocalVOIP",
    "mqtt_broker" : "192.168.235.1",  # Kumquat Pi
    #"mqtt_broker" : "broker.hivemq.com",  # Hive MQTT
    "mqtt_port" : 1883,
    "mqtt_username" : None,  # Use None for username when it is not required 
    "mqtt_password" : None,  # Use None for password when it is not required
    "apply_dst" : True,

    # Application specific secrets
    "use_oled_featherwing" : True,
    "verbose_startup" : True,
    "use_logger_sdcard" : True,
    "use_logger_rtc" : True,
    "use_crickit_motor_1" : True,
    "use_crickit_motor_2" : True,
    "use_crickit_servo_1" : True,
    "use_crickit_servo_2" : False,
    "use_crickit_servo_3" : False,
}
