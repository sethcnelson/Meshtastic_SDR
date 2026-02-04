## Changes done by Tom_Acco from the Josh Conway original
* Adjusted the GNU flow for AU.
* Rewrote python script to receive, decrypt, decode.
* Now supports multiple keys

## Credits
[crankylinuxuser/meshtastic_sdr](https://gitlab.com/crankylinuxuser/meshtastic_sdr)

## Original
This is a GnuRadio SDR project to fully build a RX and TX stack for Meshtastic.

## Installation

1. Clone repo to local machine with `git clone https://github.com/sethcnelson/Meshtastic_SDR.git`
2. Install Gnuradio and associated plugins.
3. Install the Meshtastic Python with "pip3 install meshtastic"
4. Clone and install https://github.com/tapparelj/gr-lora_sdr 
5. Open in ./meshtastic_sdr/gnuradio scripts/RX/ your relevant area and presets you want to monitor. RTLSDR has ~2.5mhz usable bandwidth so can be used with all but the Meshtastic_US_allPresets.grc as that requires 20MHz (like a HackRF One)
6. Run the flow in GnuRadio. NOTE: the flows emit data AS A server to TCP ports. Looking at the block "ZMQ PUB Sink" you can see the ports are from 20000-20007. 
7. Run the python3 program with `python3 main.py ip <SERVER> port <PORT> --preset <LongFast/MediumFast/etc>`

## Test setup

1. Create docker container with debian:latest image, mount a volume to access the setup script, and map a port for the webui (5000)
2. Initialize the container, execute the `deb-install.sh` script to install all dependancies and build gr-lora_sdr from source, clone this repo, etc.
3. Compile the GNU Radio script for headless use
```bash
cd Meshtastic_SDR/gnuradio
grcc Meshtastic_US_250KHz_RTLSDR_headless.grc
```
4. Launch tmux and in one session start the GNU Radio process
```bash
python3 Meshtastic_US_250KHz_RTLSDR_headless.py
```
5. In another session start decoder
```bash
cd ../script
python3 main.py ip <SERVER> port <PORT> --preset <LongFast/MediumFast/etc>
```
6. In another session run webui host
```bash
cd ../webui
python3 app.py
```

## tmux Quick Reference:

- `Ctrl+b` then `"` - Split horizontally
- `Ctrl+b` then `%` - Split vertically
- `Ctrl+b` then arrow keys - Switch between panes
- `Ctrl+b` then `d` - Detach (keeps running)
- `tmux attach` - Reattach later
- `Ctrl+b` then `x` - Close current pane

~~The program also accepts individual packets of data with "python3 meshtastic_gnuradio_decoder.py -i <data>" ~~

The program also supports an optional AES key list to decrypt. If you don't provide it, it uses the default 'AQ==' key for the public channel.

Note that the ports are set as:
Shortfast TCP/20000
ShortSlow TCP/20001
MediumFast TCP/20002
MediumSlow TCP/20003
LongFast TCP/20004 (COMMON!)
LongModerate TCP/20005
LongSlow TCP/20006
VeryLongSlow TCP/20007


## Purpose

An SDR can decode all the presets at the same time. Real hardware can only decode the preset in which its set to.

An SDR, depending on the amount of bandwidth captured, can decode up to all of 900MHz ISM spectrum for all LoRa channels. We only need to throw CPU at the problem.

We can now RX LoRa on non-standard frequencies, like Amateur radio bands with superb propagation. Think 6M or 10M .This also depends on getting the TX flow done. Meshtastic presets do have 250KHz, 125KHz, and 62.5KHz - so this does make LoRa usable for lower bands!

Dependency: https://github.com/tapparelj/gr-lora_sdr

Note: Meshtastic is a trademark by these fine folks! https://meshtastic.org . We wouldn't be doing SDR shenanigans without'em!

## Database Queries
The SQLlite db used to log traffic and node specifics can be queried thusly:
You can query it directly with sqlite3:                                                                        
                                                                                                                 
  ### See all known nodes                                                                                          
  `sqlite3 mesh.db "SELECT node_id, long_name, short_name, hw_model, first_seen, last_seen FROM nodes;"`           
                                                                                                                 
  ### Recent traffic                                                                                               
  `sqlite3 mesh.db "SELECT timestamp, source_name, dest_name, msg_type FROM traffic ORDER BY id DESC LIMIT 20;"`   
                                                                                                                 
  ### Traffic counts by message type                                                                               
  `sqlite3 mesh.db "SELECT msg_type, COUNT(*) as count FROM traffic GROUP BY msg_type ORDER BY count DESC;"`       
                                                                                                                 
  ### Traffic counts per node                                                                                      
  `sqlite3 mesh.db "SELECT source_name, COUNT(*) as count FROM traffic GROUP BY source_name ORDER BY count DESC;"` 
                                                                                                                 
  ### Nodes with position data                                                                                     
  `sqlite3 mesh.db "SELECT source_name, data FROM traffic WHERE msg_type = 'POSITION_APP' ORDER BY id DESC;"`      
                                                                                                                 
  ### For a dashboard/map, the position data is already being logged as JSON in the data column (latitude/longitude  
  from POSITION_APP). You could pull that with something like:                                                   
                                                                                                                 
  `sqlite3 -json mesh.db "SELECT source_name, source_id, json_extract(data, '$.latitude') as lat,                 
  json_extract(data, '$.longitude') as lon, timestamp FROM traffic WHERE msg_type = 'POSITION_APP' ORDER BY id   
  DESC;"`                          
![](public/US_all_preset_capture.png)