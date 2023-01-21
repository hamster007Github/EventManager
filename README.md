# Description
This script is a standalone and improved version of the fork [mp-eventwatcher fork](https://github.com/hamster007Github/mp-eventwatcher). All of them are based on [mp-eventwatcher](https://github.com/ccev/mp-eventwatcher).
## Features
- Automaticlly add/modify events in scanner DB (MAD) for spawnpoint changing events
- Delete quests in scanner DB (MAD) and perform "apply settings" (MAD) on start/end of quest changing events
- Delete pokémon in scanner DB (MAD) on start/end of pokemon changing events
- Telegram/Discord notification for quest reset
- Provide eventdata for scanner plugin pages to visualize current event data of eventmanager

## Recommendation MAD walker configuration to perform quest rescan
To perform an automatic quest rescan after quest deletion, you have to setup your MAD walker in a special way. Example walker setting:

| Area          | Area mode | Walker mode | Setting    |
| ------------- | --------- | ----------- | ---------- |
| quest_all     | pokestops | coords      | 1:00-6:00  |
| quest_rescan<sup>1</sup> | pokestops | coords      | 6:00-18:00 |
| pokemon       | mon_mitm  | period      | 1:10-1:00  |

<sup>1</sup>Area especially for quest rescan with limited devices/pokestops -> MAD will use this Area to rescan with e.g. smaller geofence or limited devices)

## Limitations
### No lure duration changes for events without spanwnpoint changes
MAD ignores lure_duration setting for event 'DEFAULT' (see function _extract_args_single_stop() in [DbPogoProtoSubmit.py](https://github.com/Map-A-Droid/MAD/blob/master/mapadroid/db/DbPogoProtoSubmit.py))

### Only support for MAD
Only MAD interface available, yet. But with this standalone script, it should be easy to include additional scanner systems (PRs welcome)

## Source of event data
The [pogoinfo](https://github.com/ccev/pogoinfo) from project from [ccev](https://github.com/ccev) provides regular updated JSON files with pogo data like event and raid information. For event data see: [event.json](https://github.com/ccev/pogoinfo/blob/v2/active/events.json).
All event information are grabed from there. Many thanks, ccev!

# Installation
It is highly recommended to use virtual python environment.
- create environment: `virtualenv -p python3 ~/VENVFOLDER/eventmanager_env`
- clone this branch: `git clone https://github.com/hamster007Github/EventManager.git`
- cd EventManager
- install dependencies:`~/VENVFOLDER/eventmanager_env/bin/pip3 install -r requirements.txt`
- `cp config/config.ini.example config/config.ini`
- adapt config/config.ini for your needs See [config.ini options](#config.inioptions)

# run
- script call: `~/VENVFOLDER/eventwatcher_env/bin/python3 run.py`
- available arguments for logging: `~/VENVFOLDER/eventwatcher_env/bin/python3 run.py -help`

# config.ini options
### general section
- `sleep` to define the time to wait in-between checking for new events. By default it's one hour.
- `delete_events` if you want eventmanager to delete non-needed events (including basically all you've created yourself) - by default it's set to False.
- `language` set language for Telegram and Discord notifications. Must be provided by local_default.json or local_custom.json. If no local_custom.json is provided, local_default.json is used (provides 'de' and 'en'). Default: en
- `custom_eventcache_path` optional parameter. If you want to store .eventcache file in another folder, uncomment and set absolut path. Shall end with '/'. Needed for running MAD EventManagerViewerPlugin in docker and provide .eventcache in configurated volume folder, so MAD in docker is able to access file. e.g. `custom_eventcache_path = /home/user/docker/volumes/mad/plugins/eventmanagerviewer/`
**Pokemon reset**:

- `reset_pokemon_enable` option to automatically delete obsolete pokemon from MAD database on start and end of pokemon changing event to enable MAD to rescan pokemon. true: enable function, false: disable function (default)
- `reset_pokemon_strategy` define pokemon delete strategy. ['all'(default) or 'filtered']
  - `all` delete all pokemon from databasse by SQL TRUNCATE query. Highly recommended for bigger instances
  - `filtered` delete only pokemon from database by SQL DELETE query, which are effected by eventchange. Can result in database lock issues (depends on server performance / database size

**Quest reset**:

- `reset_quests_enable` option to automatically delete quests from MAD database on start and/or end of quest changing event to enable MAD to rescan quests. true: enable function, false: disable function (default)
- `reset_quests_event_type` define event types and if you want quests to reset for their start, end or both. Syntax: "<eventtype>:end/start <eventtype2>:end/start". If you don't set `start` or `end`, both will be activated. (default: `event`). Examples:
  - `event community-day` reset quests for start and end of regular and cday events
  - `event:start` reset quests for start of regular events
  - `community-day event:end` reset quests for start and end of cday events + end of regular events
  - Available event types are `event`, `community-day`, `season`, `spotlight-hour` and `raid-hour`. The last 2 are not relevant for quest reset. Most events are of type `event`.
- `reset_quests_exclude_events` define event name text phrases, which shall be excluded for quest reset. Eventmanager checks, if an event name contain matching text. Can be used to ignore Go battle day, which only has special research and no changing pokestop quests. Separate multiple event name text phrases with comma.

## scanner section
- `db_host` scanner host adress (default: localhost)
- `db_name` scanner database name
- `db_user` database username (need select and delete access rights for `db_name`)
- `db_password` password of `db_user`

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
- `tg_questrescan_before` string which is posted additionally in configurated `tg_chat_id`, if quest reset happens before `quest_rescan_timewindow`. Will result in regular quest scan later.
- `tg_questrescan_during` string which is posted additionally in configurated `tg_chat_id`, if quest reset happens during `quest_rescan_timewindow`. Will result in quest rescan.
- `tg_questrescan_after` string which is posted additionally in configurated `tg_chat_id`, if quest reset happens after `quest_rescan_timewindow`. Will result in no quest rescan.

**Discord**

- `dc_questreset_tmpl` template string for quest delete and quest rescan notification. you can use placeholder, which will be replaced by eventmanager. Available placeholder:
  - `${event_trigger}` will be replaced by "start" or "end"
  - `${event_name}` will be replaced by english event name
- `dc_webhook_embedTitle` Discord webhook title for the embed.

# Unittests (devs only)
Only needed to support active development.
- adapt /test/config_test.ini (TBD)
- run tests (clean console output): `~/VENVFOLDER/eventwatcher_env/bin/python3 -m unittest -v`
- (optional) run tests incl. debug console logging: `~/VENVFOLDER/eventwatcher_env/bin/python3 -m test.test -v`
Remark: activate test cases from `TestEventManagerWithTestenvironment` only, if you know what you are doing :)

# madmin integration
You can have same event list as the eventwatcher plugin with this the [EventManagerViewerPlugin](https://github.com/hamster007Github/EventManagerViewerPlugin). Check repo for more information

# Todos
* [ ] remove dependencies to testenvironment for standard unit tests
* [ ] Telegram/Discord notification for pokémon reset
* [ ] check abstract class with different number arguments for function implementation
* [ ] beautify src: split into different modules, remove unused code, add useful comments, add TBDs for follow-up activities