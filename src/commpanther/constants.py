# Service States
STATE_STOPPED = "stopped"
STATE_STARTING = "starting"
STATE_IDLE = "idle"
STATE_PROCESSING = "processing"
STATE_STOPPING = "stopping"
STATE_ERROR = "error"

# Categories
CAT_URGENT = "urgent"
CAT_IMPORTANT = "important"
CAT_LATER = "later"
CAT_NO_ACTION = "no_action"

# Deadline Statuses
DEADLINE_CONFIRMED = "confirmed"
DEADLINE_UNCLEAR = "unclear"
DEADLINE_ABSENT = "absent"

# IPC Methods
METHOD_PING = "ping"
METHOD_GET_STATUS = "get_status"
METHOD_START = "start"
METHOD_STOP = "stop"
METHOD_PROCESS_NOW = "process_now"
METHOD_UPDATE_SETTINGS = "update_settings"