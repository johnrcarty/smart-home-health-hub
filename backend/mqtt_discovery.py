# Create a new file for MQTT discovery functionality

import json

def send_mqtt_discovery(mqtt_client, test_mode=True):
    """
    Send MQTT Discovery messages to Home Assistant.
    
    Args:
        mqtt_client: The connected MQTT client
        test_mode: If True, uses medical-test prefix instead of medical
    """
    discovery_prefix = "homeassistant"
    base_topic = "medical-test" if test_mode else "medical"
    
    mqtt_topic = f"{base_topic}/spo2/state"
    
    device_info = {
        "mf": "Covidien",
        "mdl": "Nellcor PM100N",
        "name": "SpO₂ Monitor",
        "ids": ["spo2_monitor"]
    }

    sensors = {
        "spo2_level": {
            "uniq_id": f"{base_topic}_sensor.spo2_level",
            "name": "SpO₂ Level",
            "stat_t": f"{mqtt_topic}",
            "template_value": "{{ value_json['spo2'] }}",
            "json_attr_t": f"{base_topic}/spo2/attributes",
            "avty_t": f"{base_topic}/spo2/availability",
            "unit_of_meas": "%",
            "stat_cla": "measurement",
        },
        "pulse_rate": {
            "uniq_id": f"{base_topic}_sensor.pulse_rate",
            "name": "Pulse Rate",
            "template_value": "{{ value_json['bpm'] }}",
            "stat_t": f"{mqtt_topic}",
            "json_attr_t": f"{base_topic}/spo2/attributes",
            "avty_t": f"{base_topic}/spo2/availability",
            "unit_of_meas": "BPM",
            "stat_cla": "measurement",
        },
        "perfusion_index": {
            "uniq_id": f"{base_topic}_sensor.perfusion_index",
            "name": "Perfusion Index",
            "template_value": "{{ value_json['pa'] }}",
            "stat_t": f"{mqtt_topic}",
            "json_attr_t": f"{base_topic}/spo2/attributes",
            "avty_t": f"{base_topic}/spo2/availability",
            "unit_of_meas": "PA",
            "stat_cla": "measurement",
        },
        "sensor_status": {
            "uniq_id": f"{base_topic}_sensor.sensor_status",
            "name": "Sensor Status",
            "template_value": "{{ value_json['status'] }}",
            "stat_t": f"{mqtt_topic}",
            "json_attr_t": f"{base_topic}/spo2/attributes",
            "avty_t": f"{base_topic}/spo2/availability",
        },
        "motion_detected": {
            "uniq_id": f"{base_topic}_sensor.motion_detected",
            "name": "Motion Detected",
            "template_value": "{{ value_json['motion'] }}",
            "stat_t": f"{mqtt_topic}",
            "json_attr_t": f"{base_topic}/spo2/attributes",
            "avty_t": f"{base_topic}/spo2/availability",
            "payload_on": "ON",
            "payload_off": "OFF",
        },
        "spo2_alarm": {
            "uniq_id": f"{base_topic}_sensor.spo2_alarm",
            "name": "SpO₂ Alarm",
            "template_value": "{{ value_json['spo2_alarm'] }}",
            "stat_t": f"{mqtt_topic}",
            "json_attr_t": f"{base_topic}/spo2/attributes",
            "avty_t": f"{base_topic}/spo2/availability",
            "payload_on": "ON",
            "payload_off": "OFF"
        },
        "hr_alarm": {
            "uniq_id": f"{base_topic}_sensor.hr_alarm",
            "name": "Heart Rate Alarm",
            "template_value": "{{ value_json['hr_alarm'] }}",
            "stat_t": f"{mqtt_topic}",
            "json_attr_t": f"{base_topic}/spo2/attributes",
            "avty_t": f"{base_topic}/spo2/availability",
            "payload_on": "ON",
            "payload_off": "OFF",
        }
    }

    for sensor_id, config in sensors.items():
        config["dev"] = device_info
        discovery_topic = f"{discovery_prefix}/sensor/{sensor_id}/config"
        json_payload = json.dumps(config)

        try:
            mqtt_client.publish(discovery_topic, json_payload, retain=True)
            print(f"[mqtt_discovery] Sent MQTT Discovery for {sensor_id} to {discovery_topic}")
        except Exception as e:
            print(f"[mqtt_discovery] Error sending discovery for {sensor_id}: {e}")