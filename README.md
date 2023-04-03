# Description
This script is a standalone and improved version of the fork [mp-eventwatcher fork](https://github.com/hamster007Github/mp-eventwatcher). All of them are based on [mp-eventwatcher](https://github.com/ccev/mp-eventwatcher).
## Features
- MAD: Automaticlly add/modify events in scanner DB (MAD) for spawnpoint changing events
- MAD: Delete quests in scanner DB (MAD) and perform "apply settings" (MAD) on start/end of quest changing events
- MAD: Delete pokémon in scanner DB (MAD) on start/end of pokemon changing events
- MAD/RDM: Telegram/Discord notification for quest reset
- MAD: Provide eventdata for scanner plugin pages to visualize current event data of eventmanager
- RDM support: Delete quests and start re-quest assignment group by RDM API interface

## Recommendation MAD walker configuration to perform quest rescan
To perform an automatic quest rescan after quest deletion, you have to setup your MAD walker in a special way. Example walker setting:

| Area         | Area mode | Walker mode | Setting    |
| ------------ | --------- | ----------- | ---------- |
| quest_all    | pokestops | coords      | 1:00-6:00  |
| quest_rescan | pokestops | coords      | 6:00-18:00 |
| pokemon      | mon_mitm  | period      | 1:10-1:00  |
*quest_rescan: area especially for quest rescan with limited devices/area*

## Example instance setting for RDM to perform quest rescan with smaller area
To perform an automatic quest rescan after quest deletion, you have to setup a Assignment Group in RDM, which include at least one Auto-Quest assignment. This Assigment can include a Auto-Quest instance with smaller area then regular Auto-Quest instance and also limited number of devices to not impact mon scans in parallel (in the following example called 'quest_rescan'). So you can do a much faster rescan for priorities areas in parallel to regular mon scanning. Example configuration:

**Instance:**
| Name         | Type       |
| ------------ | ---------- |
| quest_all    | Auto-Quest |
| quest_rescan | Auto-Quest |
*quest_rescan: area especially for quest rescan with limited devices/area*

**Auto-Assignments:**
| Source       |  Target      | Device UUID / Group | Time        |
| ------------ | ------------ | ------------------- | ----------- |
|              | quest_all    | AllDevices          | 01:00:00    |
| quest_all    | pokemon      | AllDevices          | On Complete |
| quest_all    | quest_rescan | Device1             | 05:00:00    |
| quest_rescan | pokemon      | Device1             | On Complete |

**Assignment Groups:**
| Name   | Assignments             |
| ------ | ----------------------- |
| Rescan | Device1 -> quest_rescan |

## Limitations
### MAD: No lure duration changes for events without spanwnpoint changes
MAD ignores lure_duration setting for event 'DEFAULT' (see function _extract_args_single_stop() in [DbPogoProtoSubmit.py](https://github.com/Map-A-Droid/MAD/blob/master/mapadroid/db/DbPogoProtoSubmit.py))

## Source of event data
The [pogoinfo](https://github.com/ccev/pogoinfo) from project from [ccev](https://github.com/ccev) provides regular updated JSON files with pogo data like event and raid information. For event data see: [event.json](https://github.com/ccev/pogoinfo/blob/v2/active/events.json).
All event information are grabed from there. Many thanks, ccev!

# Installation
It is highly recommended to use virtual python environment.
- create virtual python environment. Example: `python3 -m venv ~/venv/eventmanager_env`
- switch to a /home/user directory, where EventManager should be installed. Example: `cd /home/myuser`
- clone this branch: `git clone https://github.com/hamster007Github/EventManager.git`
- `cd EventManager`
- install dependencies:`~/venv/eventmanager_env/bin/pip3 install -r requirements.txt`
- `cp config/config.ini.example config/config.ini`
- adapt config/config.ini for your needs See [config.ini options](#config.inioptions)

# run
- switch to Eventmanager folder. Example: `cd ~/EventManager`
- script call: `~/venv/eventmanager_env/bin/python3 run.py`
- get available arguments for logging: `~/venv/eventmanager_env/bin/python3 run.py -help`

## PM2 ecosystem file
Based on the examples in [Installation](#Installation) you can use following ecosystem file (linux user `myuser`):
```
{
    name: 'EventManager',
    script: 'run.py',
    cwd: '/home/myuser/EventManager',
    interpreter:'/home/myuser/venv/eventmanager_env/bin/python3',
    instances: 1,
    autorestart: true,
    restart_delay: 10000,
    watch: false,
    max_memory_restart: '100M'
}
```

# config.ini options
### general section
- `sleep` to define the time to wait in-between checking for new events. By default it's one hour.
- `delete_events` if you want eventmanager to delete non-needed events (including basically all you've created yourself) - by default it's set to False.
- `language` set language for Telegram and Discord notifications. Must be provided by local_default.json or local_custom.json. If no local_custom.json is provided, local_default.json is used (provides 'de' and 'en'). Default: en
- `custom_eventcache_path` optional parameter. If you want to store .eventcache file in another folder, uncomment and set absolut path. Shall end with '/'. Needed for running MAD EventManagerViewerPlugin in docker and provide .eventcache in configurated volume folder, so MAD in docker is able to access file. e.g. `custom_eventcache_path = /home/user/docker/volumes/mad/plugins/eventmanagerviewer/`
**Pokemon reset**:

- `reset_pokemon_enable` option to automatically delete obsolete pokemon from MAD database on start and end of pokemon changing event to enable MAD to rescan pokemon. true: enable function, false: disable function (default)
- `reset_pokemon_strategy` define pokemon delete strategy. ['all' or 'filtered'(default)]
  - `all` delete all pokemon from databasse by SQL TRUNCATE query. Will not work with MAD.
  - `filtered` delete only pokemon from database by SQL DELETE query, which are effected by eventchange. Hint: cleanup your pokemon table regular, otherwise delete took to much time.

**Quest reset**:

- `reset_quests_enable` option to automatically delete quests from MAD database on start and/or end of quest changing event to enable MAD to rescan quests. true: enable function, false: disable function (default)
- `reset_quests_event_type` define event types and if you want quests to reset for their start, end or both. Syntax: "<eventtype>:end/start <eventtype2>:end/start". If you don't set `start` or `end`, both will be activated. (default: `event`). Examples:
  - `event community-day` reset quests for start and end of regular and cday events
  - `event:start` reset quests for start of regular events
  - `community-day event:end` reset quests for start and end of cday events + end of regular events
  - Available event types are `event`, `community-day`, `season`, `spotlight-hour` and `raid-hour`. The last 2 are not relevant for quest reset. Most events are of type `event`.
- `reset_quests_exclude_events` define event name text phrases, which shall be excluded for quest reset. Eventmanager checks, if an event name contain matching text. Can be used to ignore Go battle day, which only has special research and no changing pokestop quests. Separate multiple event name text phrases with comma.

## scanner section
- `scanner` General: set your scanner system ['rdm' or 'mad' (default)]
- `rescan_trigger_cmd` General: (optional) user OS shell command, which should be executed on quest reset. Can also be a shellscript with custom restart MAD. Possible examples:
  - MAD 'apply settings' on different server to restart worker: reset_trigger_cmd = sh userscripts/mad_custom_apply_settings.sh
  - MAD restart: you need your own script, which matching your setup (depends on how you start MAD (pm2, systemd, ...)
### MAD specific options
- `db_host` (optional) scanner database host adress (default: localhost)
- `db_port` (optional) scanner database port (default: 3306)
- `db_name` MAD database name
- `db_user` MAD database username (need select and delete access rights for `db_name`)
- `db_password` password of `db_user`
- `rescan_trigger_madmin_ports` MAD madmin port to call reload ('apply settings') on quest reset to reset worker. For multiple MAD instances list instance ports with comma. e.g. rescan_trigger_madmin_ports = 5000, 5001. If you don't want to use reload ('apply settings') -> comment it out.
### RDM specific options
- `rdm_api_url` RDM API url (webfrontend url incl. port). If you use RDM default, set this to http://127.0.0.1:9001
- `rdm_api_user` RDM API admin username
- `rdm_api_password` RDM API admin password
- `rdm_assignment_group` RDM assignment group name, which contain your auto-quest instances for re-quest

## telegram section
This feature informs a user, group or channel about quest resets.
- `tg_info_enable` Enable or disable Telegram notification feature. ['true' or 'false' (default)]
- `tg_bot_token` Telegram bot API token from @godfather.
- `tg_chat_id` @username or id. Separate multiple chats with comma. Example: tg_chat_id = -12345678, 87654321
- `quest_rescan_timewindow` timewindow with pattern ##-## (24h time format), in which quests are scanned. Used for inform Telegram users about possible rescan.

## discord section
This feature informs by webhook to a discord channel about quest resets.
- `dc_info_enable` Enable or disable Discord notification feature. ['true' or 'false' (default)]
- `dc_webhook_username` Discord bot username. ['Pogo Event Notification']
- `dc_webhook_url` Discord webhook url. Separate multiple webhock urls with comma. [https://discordapp.com/api/webhooks/123456789/XXXXXXXXXXXXXXXXXXXXXXX, ...]

# Locals

You can provide your own local_custom.json with locals. You can also include new languages. Language type shall match with configuration parameter `language`.

**Telegram**:

- `tg_questreset_tmpl` template string for quest delete and quest rescan notification. you can use placeholder, which will be replaced by eventmanager. Available placeholder:
  - `${event_trigger}` will be replaced by "start" or "end"
  - `${event_name}` will be replaced by english event name
  - `${rescan_str}` will be replaced by `tg_questrescan_before`, `tg_questrescan_during` or `tg_questrescan_after`, depending on actual time and `quest_rescan_timewindow`
- `tg_questrescan_outside` string which is posted additionally in configurated `tg_chat_id`, if quest reset happens outside `quest_rescan_timewindow`. Will result in no additional rescan.
- `tg_questrescan_inside` string which is posted additionally in configurated `tg_chat_id`, if quest reset happens inside `quest_rescan_timewindow`. Will result in quest rescan.

**Discord**

- `dc_questreset_tmpl` template string for quest delete and quest rescan notification. you can use placeholder, which will be replaced by eventmanager. Available placeholder:
  - `${event_trigger}` will be replaced by "start" or "end"
  - `${event_name}` will be replaced by english event name
- `dc_webhook_embedTitle` Discord webhook title for the embed.

# Unittests (devs only)
Only needed to support active development.
- adapt /test/config_test.ini (TBD)
- run tests (clean console output): `~/venv/eventmanager_env/bin/python3 -m unittest -v`
- (optional) run tests incl. debug console logging: `~/venv/eventmanager_env/bin/python3 -m test.test -v`
Remark: activate test cases from `TestEventManagerWithTestenvironment` only, if you know what you are doing :)

# madmin integration
You can have same event list as the eventwatcher plugin with this the [EventManagerViewerPlugin](https://github.com/hamster007Github/EventManagerViewerPlugin). Check repo for more information

# Todos
* [ ] Telegram/Discord notification for pokémon reset
* [ ] RDM: pokemon reset feature on event start/end