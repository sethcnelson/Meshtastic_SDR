import json

from meshtastic import mesh_pb2, admin_pb2, telemetry_pb2

class Message(object):
    def __init__(self, sourceId, destId, data):
        self.sourceId = sourceId
        self.destId = destId

        try:
            match data.portnum:
                case 0: # UNKNOWN_APP
                    self.type = "UNKNOWN_APP"

                case 1: # TEXT_MESSAGE_APP
                    self.type = "TEXT_MESSAGE_APP"
                    self.data = data.payload.decode("utf-8")

                case 2 : # REMOTE_HARDWARE_APP
                    self.type = "REMOTE_HARDWARE_APP"

                case 3 : # POSITION_APP
                    self.type = "POSITION_APP"

                    pos = mesh_pb2.Position()
                    pos.ParseFromString(data.payload)

                    self.data = {
                        "latitude": pos.latitude_i * 1e-7,
                        "longitude": pos.longitude_i * 1e-7,
                    }
                    if pos.altitude:
                        self.data["altitude"] = pos.altitude
                    if pos.precision_bits:
                        self.data["precision_bits"] = pos.precision_bits
                    if pos.sats_in_view:
                        self.data["sats_in_view"] = pos.sats_in_view
                    if pos.ground_speed:
                        self.data["ground_speed"] = pos.ground_speed
                    if pos.ground_track:
                        self.data["ground_track"] = pos.ground_track

                case 4 : # NODEINFO_APP
                    self.type = "NODEINFO_APP"
                    info = mesh_pb2.User()
                    info.ParseFromString(data.payload)
                    self.data = {
                        "id": info.id,
                        "long_name": info.long_name,
                        "short_name": info.short_name,
                        "hw_model": info.hw_model,
                        "role": info.role,
                    }
                    if info.public_key:
                        self.data["public_key"] = info.public_key.hex()

                case 5 : # ROUTING_APP
                    self.type = "ROUTING_APP"

                    routing = mesh_pb2.Routing()
                    routing.ParseFromString(data.payload)
                    self.data = str(routing)

                case 6 : # ADMIN_APP
                    self.type = "ADMIN_APP"

                    admin = admin_pb2.AdminMessage()
                    admin.ParseFromString(data.payload)
                    self.data = str(admin)

                case 7 : # TEXT_MESSAGE_COMPRESSED_APP
                    self.type = "TEXT_MESSAGE_COMPRESSED_APP"

                case 10 : # DETECTION_SENSOR_APP
                    self.type = "DETECTION_SENSOR_APP"

                case 32 : # REPLY_APP
                    self.type = "REPLY_APP"

                case 33 : # IP_TUNNEL_APP
                    self.type = "IP_TUNNEL_APP"

                case 34 : # PAXCOUNTER_APP
                    self.type = "PAXCOUNTER_APP"

                case 64 : # SERIAL_APP
                    self.type = "SERIAL_APP"

                case 65 : # STORE_FORWARD_APP
                    self.type = "STORE_FORWARD_APP"

                    sfwd = mesh_pb2.StoreAndForward()
                    sfwd.ParseFromString(data.payload)
                    self.data = str(sfwd)

                case 67 : # TELEMETRY_APP
                    self.type = "TELEMETRY_APP"

                    telemetry = telemetry_pb2.Telemetry()
                    telemetry.ParseFromString(data.payload)

                    tdata = {}
                    if telemetry.time:
                        tdata["time"] = telemetry.time

                    if telemetry.HasField("device_metrics"):
                        dm = telemetry.device_metrics
                        tdata["telemetry_type"] = "device"
                        if dm.battery_level:
                            tdata["battery_level"] = dm.battery_level
                        if dm.voltage:
                            tdata["voltage"] = round(dm.voltage, 2)
                        if dm.channel_utilization:
                            tdata["channel_utilization"] = round(dm.channel_utilization, 2)
                        if dm.air_util_tx:
                            tdata["air_util_tx"] = round(dm.air_util_tx, 2)
                        if dm.uptime_seconds:
                            tdata["uptime_seconds"] = dm.uptime_seconds

                    elif telemetry.HasField("environment_metrics"):
                        em = telemetry.environment_metrics
                        tdata["telemetry_type"] = "environment"
                        if em.temperature:
                            tdata["temperature"] = round(em.temperature, 1)
                        if em.relative_humidity:
                            tdata["relative_humidity"] = round(em.relative_humidity, 1)
                        if em.barometric_pressure:
                            tdata["barometric_pressure"] = round(em.barometric_pressure, 2)
                        if em.gas_resistance:
                            tdata["gas_resistance"] = round(em.gas_resistance, 2)
                        if em.voltage:
                            tdata["voltage"] = round(em.voltage, 2)
                        if em.current:
                            tdata["current"] = round(em.current, 2)
                        if em.iaq:
                            tdata["iaq"] = em.iaq
                        if em.distance:
                            tdata["distance"] = round(em.distance, 2)
                        if em.lux:
                            tdata["lux"] = round(em.lux, 1)
                        if em.white_lux:
                            tdata["white_lux"] = round(em.white_lux, 1)
                        if em.ir_lux:
                            tdata["ir_lux"] = round(em.ir_lux, 1)
                        if em.uv_lux:
                            tdata["uv_lux"] = round(em.uv_lux, 1)
                        if em.wind_direction:
                            tdata["wind_direction"] = em.wind_direction
                        if em.wind_speed:
                            tdata["wind_speed"] = round(em.wind_speed, 1)
                        if em.wind_gust:
                            tdata["wind_gust"] = round(em.wind_gust, 1)
                        if em.wind_lull:
                            tdata["wind_lull"] = round(em.wind_lull, 1)
                        if em.radiation:
                            tdata["radiation"] = round(em.radiation, 2)
                        if em.rainfall_1h:
                            tdata["rainfall_1h"] = round(em.rainfall_1h, 2)
                        if em.rainfall_24h:
                            tdata["rainfall_24h"] = round(em.rainfall_24h, 2)
                        if em.soil_moisture:
                            tdata["soil_moisture"] = em.soil_moisture
                        if em.soil_temperature:
                            tdata["soil_temperature"] = round(em.soil_temperature, 1)

                    elif telemetry.HasField("power_metrics"):
                        pm = telemetry.power_metrics
                        tdata["telemetry_type"] = "power"
                        channels = []
                        for i in range(1, 9):
                            v = getattr(pm, f"ch{i}_voltage", 0)
                            c = getattr(pm, f"ch{i}_current", 0)
                            if v or c:
                                channels.append({"ch": i, "voltage": round(v, 3), "current": round(c, 3)})
                        if channels:
                            tdata["channels"] = channels

                    elif telemetry.HasField("air_quality_metrics"):
                        aq = telemetry.air_quality_metrics
                        tdata["telemetry_type"] = "air_quality"
                        for f in ["pm10_standard", "pm25_standard", "pm100_standard",
                                  "pm10_environmental", "pm25_environmental", "pm100_environmental",
                                  "co2"]:
                            val = getattr(aq, f, 0)
                            if val:
                                tdata[f] = val
                        for f in ["particles_03um", "particles_05um", "particles_10um",
                                  "particles_25um", "particles_50um", "particles_100um"]:
                            val = getattr(aq, f, 0)
                            if val:
                                tdata[f] = val

                    elif telemetry.HasField("local_stats"):
                        ls = telemetry.local_stats
                        tdata["telemetry_type"] = "local_stats"
                        if ls.uptime_seconds:
                            tdata["uptime_seconds"] = ls.uptime_seconds
                        if ls.channel_utilization:
                            tdata["channel_utilization"] = round(ls.channel_utilization, 2)
                        if ls.air_util_tx:
                            tdata["air_util_tx"] = round(ls.air_util_tx, 2)
                        if ls.num_packets_tx:
                            tdata["num_packets_tx"] = ls.num_packets_tx
                        if ls.num_packets_rx:
                            tdata["num_packets_rx"] = ls.num_packets_rx
                        if ls.num_packets_rx_bad:
                            tdata["num_packets_rx_bad"] = ls.num_packets_rx_bad
                        if ls.num_online_nodes:
                            tdata["num_online_nodes"] = ls.num_online_nodes
                        if ls.num_total_nodes:
                            tdata["num_total_nodes"] = ls.num_total_nodes
                        if ls.num_rx_dupe:
                            tdata["num_rx_dupe"] = ls.num_rx_dupe
                        if ls.num_tx_relay:
                            tdata["num_tx_relay"] = ls.num_tx_relay
                        if ls.num_tx_relay_canceled:
                            tdata["num_tx_relay_canceled"] = ls.num_tx_relay_canceled
                        if ls.num_tx_dropped:
                            tdata["num_tx_dropped"] = ls.num_tx_dropped
                        if ls.noise_floor:
                            tdata["noise_floor"] = ls.noise_floor

                    elif telemetry.HasField("health_metrics"):
                        hm = telemetry.health_metrics
                        tdata["telemetry_type"] = "health"
                        if hm.heart_bpm:
                            tdata["heart_bpm"] = hm.heart_bpm
                        if hm.spO2:
                            tdata["spO2"] = hm.spO2
                        if hm.temperature:
                            tdata["temperature"] = round(hm.temperature, 1)

                    else:
                        tdata["telemetry_type"] = "unknown"
                        tdata["raw"] = str(telemetry)

                    self.data = tdata

                case 68 : # ZPS_APP
                    self.type = "ZPS_APP"

                    z_info = mesh_pb2.zps()
                    z_info.ParseFromString(data.payload)
                    self.data = str(z_info)

                case 69 : # SIMULATOR_APP
                    self.type = "SIMULATOR_APP"

                case 70 : # TRACEROUTE_APP
                    self.type = "TRACEROUTE_APP"

                    trct = mesh_pb2.RouteDiscovery()
                    trct.ParseFromString(data.payload)
                    self.data = str(trct)

                case 71 : # NEIGHBORINFO_APP
                    self.type = "NEIGHBORINFO_APP"

                    ninfo = mesh_pb2.NeighborInfo()
                    ninfo.ParseFromString(data.payload)
                    self.data = str(ninfo)

                case 72 : # ATAK_PLUGIN
                    self.type = "ATAK_PLUGIN"

                case 73 : # MAP_REPORT_APP
                    self.type = "MAP_REPORT_APP"

                    mrpt = mesh_pb2.MapReport()
                    mrpt.ParseFromString(data.payload)
                    self.data = str(mrpt)

                case 74 : # POWERSTRESS_APP
                    self.type = "POWERSTRESS_APP"

                case 256 : # PRIVATE_APP
                    self.type = "PRIVATE_APP"

                case 257 : # ATAK_FORWARDER
                    self.type = "ATAK_FORWARDER"

                case _ : # UNKNOWN 
                    self.type = "UNKNOWN"
        except Exception as e:
            print(f"[ERROR] {e}")

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)