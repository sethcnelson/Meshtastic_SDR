import argparse
import base64
import json
import zmq
import time

from packet import Packet
from util import compute_channel_hash
from db import init_db, upsert_node, log_traffic, log_raw_packet, resolve_name, close_db

# The default Meshtastic public key bytes (AQ== expanded)
DEFAULT_KEY_BYTES = base64.b64decode("1PG7OiApB1nwvP+rz05pAQ==")

#reads keys from file called 'keys'
parser = argparse.ArgumentParser(description = "Process incoming command parmeters")
parser.add_argument("ip", action = "store", help = "IP Address.")
parser.add_argument("port", action = "store", help = "Port")
parser.add_argument("-d", "--debug", action = "store_true", dest = "debug", help = "Print more debug messages")
parser.add_argument("-s", "--save", action = "store_true", dest = "save", help = "Save packets to disk")
parser.add_argument("-p", "--preset", action = "store", dest = "preset", default = "LongFast", help = "Modem preset name, used as default channel name (default: LongFast)")
args = parser.parse_args()

debug = False
save = False

def validate_aes_key(key = None):
    if not key:
        return False

    if debug:
        print(f"[DEBUG] Validating key: {key}")

    try:
        key_len = len(base64.b64decode(key).hex())

        if key_len == 2:
            key = f"1PG7OiApB1nwvP+rz05p{key}"
            key_len = len(base64.b64decode(key).hex())

            if debug:
                print(f"[DEBUG] Added Meshtastic static key to 2 bit key: {key}")

        if debug:
            print(f"[DEBUG] key_len: {key_len}")

        if (key_len == 32 or key_len == 64):
            pass
        else:
            return False

        if debug:
            print(f"[DEBUG] Key valid")
            print("-"*50)

        return key
    except Exception as e:
        return False

def handle_packet(pkt = None):
    packet = Packet(pkt)

    print("-" * 20, " PACKET ", "-" * 20)
    print(f"[INFO] timestamp: {packet.get_timestamp()}")

    if save:
        print(f"[INFO] Saving, as requested...")
        packet.save()
    
    if debug:
        print(f"[DEBUG] Src: {packet.get_source()}")
        print(f"[DEBUG] Dest: {packet.get_dest()}")
        print(f"[DEBUG] PacketId: {packet.get_packet_id()}")
        print(f"[DEBUG] Flags: {packet.get_flags()}")
        print(f"[DEBUG] ChannelHash: {packet.get_channel_hash()}")
        print(f"[DEBUG] Data: {packet.get_data()}")
    
    decrypted = False
    matched_key = None

    for key in keys:
        try:
            decrypted = packet.decrypt(key)
            matched_key = key
            break
        except Exception as e:
            continue

    # Determine encryption type for the matched key
    encryption_type = None
    if decrypted and matched_key:
        try:
            is_public = base64.b64decode(matched_key) == DEFAULT_KEY_BYTES
        except Exception:
            is_public = False
        encryption_type = "public" if is_public else "private"

    # Parse flags byte: bits 0-2 = hop_limit, bit 3 = want_ack, bit 4 = via_mqtt,
    # bits 5-7 = hop_start (firmware 2.1+)
    flags_raw = packet.get_flags()
    hop_limit = None
    hop_start = None
    want_ack = False
    via_mqtt = False
    if flags_raw:
        try:
            flags_int = int(flags_raw, 16)
            hop_limit = flags_int & 0x07
            want_ack = bool(flags_int & 0x08)
            via_mqtt = bool(flags_int & 0x10)
            hop_start = (flags_int >> 5) & 0x07
        except (ValueError, TypeError):
            pass

    # Log every packet to packets_raw (decrypted or not)
    raw_size = len(pkt) if pkt else 0
    log_raw_packet(
        timestamp=packet.get_timestamp(),
        source_id=packet.get_source(),
        dest_id=packet.get_dest(),
        packet_id=packet.get_packet_id(),
        channel_hash=packet.get_channel_hash(),
        flags=flags_raw,
        hop_limit=hop_limit,
        hop_start=hop_start,
        want_ack=want_ack,
        via_mqtt=via_mqtt,
        packet_size=raw_size,
        decrypted=decrypted,
        key_used=encryption_type,
    )

    if decrypted:
        pkt_hash = packet.get_channel_hash()
        channel_name = channel_map.get(pkt_hash)
        if channel_name:
            print(f"[INFO] channel: {channel_name}")
        else:
            print(f"[INFO] channel: unknown (hash: {pkt_hash})")

        message = packet.get_message()

        # Handle cases where message parsing fails or returns incomplete data
        if message is None:
            print("[WARN] Failed to parse message from decrypted packet")
            print("-" * 50)
            return

        msg_type = getattr(message, 'type', 'UNKNOWN')
        msg_data = getattr(message, 'data', None)

        # Upsert node info before resolving names so the name is immediately available
        if msg_type == "NODEINFO_APP" and isinstance(msg_data, dict):
            upsert_node(
                node_id=packet.get_source(),
                long_name=msg_data.get("long_name"),
                short_name=msg_data.get("short_name"),
                hw_model=msg_data.get("hw_model"),
                role=msg_data.get("role"),
                public_key=msg_data.get("public_key"),
                timestamp=packet.get_timestamp(),
            )

        # Display resolved names
        src_name = resolve_name(packet.get_source())
        dst_name = resolve_name(packet.get_dest())
        print(f"[INFO] from: {src_name}")
        print(f"[INFO] to:   {dst_name}")

        log_traffic(
            timestamp=packet.get_timestamp(),
            source_id=packet.get_source(),
            dest_id=packet.get_dest(),
            packet_id=packet.get_packet_id(),
            channel_hash=pkt_hash,
            channel_name=channel_name,
            port_num=getattr(message, 'portnum', None),
            msg_type=msg_type,
            data=msg_data,
            key_used=encryption_type,
            via_mqtt=via_mqtt,
            hop_start=hop_start,
            hop_limit=hop_limit,
        )

        try:
            message_json = message.to_json()
            if isinstance(message_json, str):
                message_json = json.loads(message_json)
            print("message:", json.dumps(message_json, indent=2))
        except Exception as e:
            print(f"[WARN] Failed to serialize message: {e}")
            print(f"message: (type={msg_type}, data={msg_data})")
    else:
        print("[WARN] no suitable key!")

    print("-" * 50)

def listen_on_network(ip = None, port = None, keys = []):
    if not ip or not port:
        raise Exception("Missing IP or Port!")
    if not keys:
        raise Exception("Missing keys- check 'key' file and add one or more entries!")

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect("tcp://" + ip + ":" + port)
    socket.setsockopt(zmq.SUBSCRIBE, b'')

    print(f"Socket <tcp://{ip}:{port}> listening...")

    while True:
        if socket.poll(10) != 0:
            pkt = socket.recv()
            try:
                handle_packet(pkt)
            except Exception as e:
                print(f"[ERROR] Failed to process packet: {e}")
                if debug:
                    import traceback
                    traceback.print_exc()
        else:
            time.sleep(0.1)

if __name__ == "__main__":
    if args.debug:
        debug = True

    if args.save:
        save = True

    init_db(debug=debug)

    try:
        with open("keys", "r") as file:
            temp_keys = [line.strip() for line in file]
    except Exception as e:
        temp_keys = ["1PG7OiApB1nwvP+rz05pAQ=="]

    keys = []
    channel_map = {}
    preset = args.preset

    for entry in temp_keys:
        if not entry or entry.startswith("#"):
            continue

        # Support optional name:key format (colon is unambiguous since base64 never contains ':')
        if ":" in entry:
            name, raw_key = entry.split(":", 1)
        else:
            name = None
            raw_key = entry

        valid_key = validate_aes_key(raw_key)

        if not valid_key:
            print(f"[WARN] Key '{raw_key}' is not a valid AES 128/256 key!")
        else:
            keys.append(valid_key)

            # Build channel hash mapping using the expanded key (firmware hashes the full key)
            channel_name = name if name else preset
            h = compute_channel_hash(channel_name, valid_key)
            channel_map[h] = channel_name

            if debug:
                print(f"[DEBUG] Registered channel hash '{h}' -> '{channel_name}' (key: {raw_key})")

    if len(keys) > 0:
        print(f"[INFO] Loaded {len(keys)} keys")
    else:
        print(f"[WARN] No keys loaded.")

    try:
        listen_on_network(args.ip, args.port, keys)
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
    finally:
        close_db()

